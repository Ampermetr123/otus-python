#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import gzip
import sys
import glob
import logging
import collections
from threading import Thread, Event
from queue import Queue

from optparse import OptionParser
# brew install protobuf
# protoc  --python_out=. ./appsinstalled.proto
# pip install protobuf
import appsinstalled_pb2
# pip install python-memcached
import memcache

NORMAL_ERR_RATE = 0.01
WIN_SIZE = 10000

AppsInstalled = collections.namedtuple("AppsInstalled",
                                       ["dev_type", "dev_id", "lat", "lon", "apps"])


def dot_rename(path):
    head, fn = os.path.split(path)
    # atomic in most cases
    os.rename(path, os.path.join(head, "." + fn))


def parse_appsinstalled(line):
    line_parts = line.strip().split(b"\t")
    if len(line_parts) < 5:
        return
    dev_type, dev_id, lat, lon, raw_apps = line_parts
    if not dev_type or not dev_id:
        return
    try:
        apps = [int(a.strip()) for a in raw_apps.split(b",")]
    except ValueError:
        apps = [int(a.strip()) for a in raw_apps.split(b",") if a.isidigit()]
        logging.info("Not all user apps are digits: `%s`" % line)
    try:
        lat, lon = float(lat), float(lon)
    except ValueError:
        logging.info("Invalid geo coords: `%s`" % line)
    return AppsInstalled(dev_type, dev_id, lat, lon, apps)


class CacheWriter(Thread):
    def __init__(self, addr, input_queue, dry_run=False):
        self.input_queue = input_queue
        self.client = memcache.Client([addr], socket_timeout=1, debug=1)
        self.dry_run = dry_run
        self.client_addr = addr
        super().__init__()
        self.name = 'Thread-CacheWriter(%s)' % (self.client_addr)

    def stop(self):
        self.input_queue.put({})

    def run(self):
        logging.debug('Started')
        sent = lost = 0

        while True:
            data = self.input_queue.get()
            if len(data) == 0:
                break
            if not self.dry_run:
                errlist = self.client.set_multi(data)
                sent = sent + len(data) - len(errlist)
                lost = lost + len(errlist)
            else:
                logging.debug("%s <- %s" % (self.client_addr, data))
            self.input_queue.task_done()

        self.client.disconnect_all()
        logging.debug('Finished with sent=%s and lost=%s records' % (sent, lost))


class FileReader(Thread):
    def __init__(self, fn, ev, output_queue):
        self.ev = ev
        self.fn = fn
        self.output_queue = output_queue
        super().__init__()
        self.name = 'Thread-FileReader (%s)' % fn

    def run(self):
        logging.debug('Started')
        with gzip.open(self.fn) as fd:
            while True:
                lines = fd.readlines(WIN_SIZE)
                if len(lines) == 0:
                    break
                self.output_queue.put(list(lines))
                lines.clear()
                # Waiting for processor needs new data
                self.ev.wait()

        dot_rename(self.fn)
        logging.debug('Finished')


class Processor(Thread):
    def __init__(self, ev, input_queue, queue_by_dev):
        self.ev = ev
        self.input_queue = input_queue
        self.queue_by_dev = queue_by_dev
        self.processed = 0
        self.errors = 0
        super().__init__()
        self.name = 'Thread-Processor'

    def stop(self):
        self.input_queue.put([])

    def run(self):
        logging.debug('Processor started')
        buffered_lines = {}
        for k in self.queue_by_dev:
            buffered_lines[k] = {}  # dict key->val for memcache

        while True:
            lines = self.input_queue.get()
            if self.input_queue.qsize() < 100:
                self.ev.set()
            else:
                self.ev.clear()

            # finished?
            if len(lines) == 0:
                err_rate = (float(self.errors) / self.processed) if self.processed > 0 else 0
                if err_rate < NORMAL_ERR_RATE:
                    logging.info("Acceptable error rate (%s). Successfull load %s records"
                                 % (err_rate, self.processed))
                else:
                    logging.error("High error rate (%s > %s). Failed load"
                                  % (err_rate, NORMAL_ERR_RATE))
                logging.debug('Processor finished')
                return

            # converting and sorting lines by dev
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                appsinstalled = parse_appsinstalled(line)
                if not appsinstalled:
                    self.errors += 1
                    continue

                if appsinstalled.dev_type not in self.queue_by_dev:
                    self.errors += 1
                    logging.error("Unknow device type: %s" % appsinstalled.dev_type)
                else:
                    ua = appsinstalled_pb2.UserApps()
                    ua.lat = appsinstalled.lat
                    ua.lon = appsinstalled.lon
                    ua.apps.extend(appsinstalled.apps)
                    key = b"%s:%s" % (appsinstalled.dev_type, appsinstalled.dev_id)
                    packed = ua.SerializeToString()
                    buffered_lines[appsinstalled.dev_type][key] = packed
                    self.processed += 1

            self.input_queue.task_done()

            # sending data to CacheWriters
            for dt, dd in buffered_lines.items():
                if len(dd) > 0:
                    self.queue_by_dev[dt].put(dict(dd))
                    dd.clear()


def main(options):
    device_memc = {
        b"idfa": options.idfa,
        b"gaid": options.gaid,
        b"adid": options.adid,
        b"dvid": options.dvid,
    }

    # prepare cache-writers
    device_to_queue = {}
    cache_writers = []
    for k in device_memc.keys():
        q = Queue()
        device_to_queue[k] = q
        w = CacheWriter(device_memc[k], q, options.dry)
        cache_writers.append(w)
        w.start()

    start_read_event = Event()
    input_queue = Queue()
    processor = Processor(start_read_event, input_queue, device_to_queue)
    processor.start()

    # start file-readers
    readers = []
    for fn in glob.iglob(options.pattern):
        reader = FileReader(fn, start_read_event, input_queue)
        readers.append(reader)
        reader.start()

    # waiting the end
    for r in readers:
        r.join()
    processor.stop()
    processor.join()
    for w in cache_writers:
        w.stop()
        w.join()
    
    logging.info('All task done!')


def prototest():
    sample = b"idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23\ngaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424"
    for line in sample.splitlines():
        dev_type, dev_id, lat, lon, raw_apps = line.strip().split(b"\t")
        apps = [int(a) for a in raw_apps.split(b",") if a.isdigit()]
        lat, lon = float(lat), float(lon)
        ua = appsinstalled_pb2.UserApps()
        ua.lat = lat
        ua.lon = lon
        ua.apps.extend(apps)
        packed = ua.SerializeToString()
        unpacked = appsinstalled_pb2.UserApps()
        unpacked.ParseFromString(packed)
        assert ua == unpacked


if __name__ == '__main__':
    op = OptionParser()
    op.add_option("-t", "--test", action="store_true", default=False)
    op.add_option("-l", "--log", action="store", default=None)
    op.add_option("-v", "--verbose", action="store_true", default=False)
    op.add_option("--dry", action="store_true", default=False)
    op.add_option("--pattern", action="store", default="./*.tsv.gz")
    op.add_option("--idfa", action="store", default="127.0.0.1:33013")
    op.add_option("--gaid", action="store", default="127.0.0.1:33014")
    op.add_option("--adid", action="store", default="127.0.0.1:33015")
    op.add_option("--dvid", action="store", default="127.0.0.1:33016")
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log,
                        level=logging.INFO if not (opts.dry or opts.verbose) else logging.DEBUG,
                        format='[%(asctime)s](%(threadName)-9s) %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S')
    if opts.test:
        prototest()
        sys.exit(0)

    logging.info("Memc loader started with options: %s" % opts)
    try:
        main(opts)
    except Exception as e:
        logging.exception("Unexpected error: %s" % e)
        sys.exit(1)
