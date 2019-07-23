#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import subprocess
from signal import CTRL_C_EVENT
import time
from functools import update_wrapper
from optparse import OptionParser
import logging
import os
import gzip
from os.path import exists

import memcache
import appsinstalled_pb2
import memc_load_new

MEMCACHED_PATH = "./task/memcached/memcached.exe"
MEMCACHED_PORTS = (33013, 33014, 33015, 33016)


def duration_report(func):
    def wrapper(*args, **kwargs):
        t0= time.time()
        retval = func(*args, **kwargs)
        t1 = time.time()
        print("%s processed in %s sec" % (func.__name__, (t1-t0)))
        return retval
    return update_wrapper(wrapper, func)


def finish_proc(server_proc):
    server_proc.send_signal(CTRL_C_EVENT)
    try:
        server_proc.wait(0.5)
    except subprocess.TimeoutExpired:
        server_proc.kill()
    # On Win10 machine even kill doens't work ! - So control again
    if server_proc.returncode is None:
        server_proc.terminate()
    else:
        print('Process %s stopped with code %s' % (server_proc.pid, server_proc.returncode))
    # Check again
    if server_proc.returncode is None:
        print('Unable to shut down process (pid = %s). Do it manualy!!! ' % server_proc.pid)
    else:
        print('Process (pid = %s) terminated ' % server_proc.pid)


class TestMemcLoad(unittest.TestCase):
    def setUp(self):
        # starting memcache servers
        self.processes = []
        for p in MEMCACHED_PORTS:
            server_proc = subprocess.Popen([MEMCACHED_PATH, '-p', str(p)], shell=False,
                                           creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP))
            print('Memcached started on port %s (pid = %s)' % (p, server_proc.pid))
            self.processes.append(server_proc)
        super().setUp()

    def tearDown(self):
        for proc in self.processes:
            finish_proc(proc)
        super().tearDown()

    @duration_report
    def test_sample(self):
        def get_packed(recordline):
            dev_type, dev_id, lat, lon, raw_apps = recordline.strip().split(b"\t")
            apps = [int(a) for a in raw_apps.split(b",") if a.isdigit()]
            lat, lon = float(lat), float(lon)
            ua = appsinstalled_pb2.UserApps()
            ua.lat = lat
            ua.lon = lon
            ua.apps.extend(apps)
            packed = ua.SerializeToString()
            key = b'%s:%s' % (dev_type, dev_id)
            return dev_type, key, packed

        # creating sample file
        sample_file = './mysimpletest.gz'
        sample_dotfile = './.mysimpletest.gz'
        sample_data = [b'idfa\t1rfw452y52g2gq4g\t55.55	42.42\t2423,43,567,3,7,23',
                       b'idfa\t2rfw452y52g2gq4g\t55.55	42.42\t3423,43,567,3,7,23',
                       b'idfa\t3rfw452y52g2gq4g\t55.55	42.42\t4423,43,567,3,7,23',
                       b'gaid\t1rfw452y52g2gq4g\t55.55	42.42\t5423,43,567,3,7,23',
                       b'gaid\t2rfw452y52g2gq4g\t55.55	42.42\t6423,43,567,3,7,23',
                       b'gaid\t3rfw452y52g2gq4g\t55.55	42.42\t7423,43,567,3,7,23',]

        if not exists(sample_file):
            f = gzip.open(sample_file, 'wb')
            for r in sample_data:
                f.write(r)
                f.write(b'\n')
            f.close()

        if exists(sample_dotfile):
            os.remove(sample_dotfile)

        # processing sample file
        op = OptionParser()
        op.add_option("-t", "--test", action="store_true", default=False)
        op.add_option("-l", "--log", action="store", default=None)
        op.add_option("--dry", action="store_true", default=False)
        op.add_option("--pattern", action="store", default=sample_file)
        op.add_option("--idfa", action="store", default="127.0.0.1:%s" % MEMCACHED_PORTS[0])
        op.add_option("--gaid", action="store", default="127.0.0.1:%s" % MEMCACHED_PORTS[1])
        op.add_option("--adid", action="store", default="127.0.0.1:%s" % MEMCACHED_PORTS[2])
        op.add_option("--dvid", action="store", default="127.0.0.1:%s" % MEMCACHED_PORTS[3])
        (opts, args) = op.parse_args([])
        memc_load_new.main(opts)

        # checking data in memcache
        clients = {}
        clients[b'idfa'] = memcache.Client(["127.0.0.1:%s" % MEMCACHED_PORTS[0]])
        clients[b'gaid'] = memcache.Client(["127.0.0.1:%s" % MEMCACHED_PORTS[1]])
        for r in sample_data:
            dev_type, key, packed = get_packed(r)
            val = clients[dev_type].get(key)
            self.assertEqual(packed, val)

        for c in clients:
            clients[c].disconnect_all()        
        self.assertTrue(exists(sample_dotfile))


    @unittest.skip('Demonstration of procesing huge files is skipped')
    @duration_report
    def test_huge(self):
        op = OptionParser()
        op.add_option("-t", "--test", action="store_true", default=False)
        op.add_option("-l", "--log", action="store", default=None)
        op.add_option("--dry", action="store_true", default=False)
        op.add_option("--pattern", action="store", default="./*.tsv.gz")
        op.add_option("--idfa", action="store", default="127.0.0.1:"+MEMCACHED_PORTS[0])
        op.add_option("--gaid", action="store", default="127.0.0.1:"+MEMCACHED_PORTS[1])
        op.add_option("--adid", action="store", default="127.0.0.1:"+MEMCACHED_PORTS[2])
        op.add_option("--dvid", action="store", default="127.0.0.1:"+MEMCACHED_PORTS[3])
        (opts, args) = op.parse_args([])
        memc_load_new.main(opts)


if __name__ == "__main__":
    logging.basicConfig(filename=None, level=logging.DEBUG,
                        format='[%(asctime)s](%(threadName)-9s) %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S')
    unittest.main()
