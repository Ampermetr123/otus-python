#!/usr/bin/env python
# -*- coding: utf-8 -*-

# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$htt p_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

import sys
import argparse
import json
import logging
import re
import gzip
import os
from os.path import isfile, join, exists
from collections import namedtuple
from numpy import median
from string import Template


config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log",
    "LOGGER_FILENAME": None
}


def setup_logger(logger_filename: str):
    """Setting up logger"""
    # todo Read more about logger and check about unicode in output file
    logging.basicConfig(level=logging.DEBUG, filename=logger_filename, filemode='w',
                        format='[%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S')


def log():
    """Returns application logger"""
    return logging.getLogger(sys.argv[0] + "_logger")


def reload_config(default_cfg):
    """Checks command line parameters and return config structure or empty dict if error"""
    parser = argparse.ArgumentParser(description="Log analyzer OTUS Phyton hometask")
    parser.add_argument('--config', default="./log_analyzer.cfg",
                         help='configuration file in JSON format (default is ./log_analyzer.cfg)')
    args = parser.parse_args()
    result_cfg = {}
    with open(args.config, "rb") as f:
        file_config = json.load(f)
        for key, val in default_cfg.items():
            result_cfg[key] = file_config[key] if key in file_config else val
    return result_cfg


def get_latest_logfile_info(folder_path) -> namedtuple('FileDescription', 'path date'):
    """Looks for latest nginx-access-ui.. log file in the folder_path"""
    FileDescription = namedtuple('FileDescription', 'path date')
    ret_val = FileDescription(None, 0)
    regexp_filename = re.compile("(nginx-access-ui.log-\d{8}\.gz)|(nginx-access-ui.log-\d{8})")
    for file_name in os.listdir(folder_path):
        full_path_name = join(folder_path, file_name)
        if isfile(full_path_name) and regexp_filename.fullmatch(file_name):
            file_date = int(re.search("\d{8}", file_name).group())
            if file_date > ret_val.date:
                ret_val = FileDescription(full_path_name,file_date)
    return ret_val


class WrongFileToParseException(Exception):
    pass


def parse_next_line(logfile_name, error_threshold):
    """Generator, returns (url,request_time) for next line. Raises WrongFileToParseException on error threshold"""
    good_parse = 0
    bad_parse = 0
    regexp_url = re.compile('((GET)|(POST)|(HEAD)|(PUT)|(OPTIONS)|(CONNECT)|(TRACE)|(PATCH)|(DELETE)) .+ HTTP/\d\.\d')
    regexp_time = re.compile('" \d+\.\d{1,3}\s')
    f = gzip.open(logfile_name) if logfile_name.endswith('.gz') else open(logfile_name, "rb")

    for s in f:
        line=s.decode(encoding='utf-8')
        match_url = regexp_url.search(line)
        if not match_url:
            bad_parse += 1
            continue
        url = match_url.group().split(sep=' ')[1]
        match_time = regexp_time.search(line, match_url.span()[1])
        if not match_time:
            bad_parse += 1
            continue
        good_parse += 1
        time = float(match_time.group()[2:-1])
        yield (url, time)

    f.close()
    log().debug('{} lines parsed from {}'.format(good_parse, good_parse+bad_parse))

    failure_perc = 100 if good_parse+bad_parse == 0 else bad_parse*100//(good_parse+bad_parse)
    if  failure_perc > error_threshold:
        raise WrongFileToParseException("File format error: "
                        "{}% lines wasn't parsed successfully".format(failure_perc))


def analyse_log_file(log_filename, error_threshold=50):
    """Parses log file and returns statistic data (list of dict).
    Raises WrongFileToParseException if error_threshold% of lines couldn't be parsed """
    url_dict = {}
    total_requests_time = 0.0
    total_requests_count = 0
    for (url, time) in parse_next_line(log_filename, error_threshold):
        total_requests_time += time
        total_requests_count += 1
        if url not in url_dict:
            url_dict[url] = [time]
        else:
            url_dict[url].append(time)

    stat_db = []
    for url, reqtime_list in url_dict.items():
        val = dict()
        val['count'] = len(reqtime_list)
        val['time_sum'] = sum(reqtime_list)
        val['time_max'] = max(reqtime_list)
        val['time_avg'] = val['time_sum'] / val['count']
        val['url'] = url
        val['time_med'] = median(reqtime_list)
        val['time_perc'] = val['time_sum'] * 100 / total_requests_time
        val['count_perc'] = len(reqtime_list)*100 / total_requests_count
        stat_db.append(val)
    return stat_db


def generate_report(data, report_template, report_filename, report_size=None):
    """Writes report of statistic data to file. """
    if report_size is None:
        report_size = len(data)
    if report_size < len(data):
        selected = sorted(data, key=lambda p:p['time_sum'], reverse=True)
        data = selected[:report_size]

    # converts floats to string for better view in report
    for d in data:
        d['time_med'] = "%.3f" % (d['time_med'])
        d['time_perc'] = "%.3f" % (d['time_perc'])
        d['time_avg'] = "%.3f" % (d['time_avg'])
        d['count_perc'] = "%.3f" % (d['count_perc'])
        d['time_sum'] = "%.3f" % (d['time_sum'])

    json_str = json.dumps(data)

    with open(report_template, 'r', encoding='utf-8') as tf:
        template = Template(tf.read())
    with open(report_filename, 'w', encoding='utf-8') as of:
        of.write(template.safe_substitute(table_json=json_str))


def main(default_cfg):
    try:
        # Starting up
        cfg = reload_config(default_cfg)
        setup_logger(cfg["LOGGER_FILENAME"])
    except Exception as ex:
        log().error('Configuration load failure: '+str(ex))
        return 1

    try:
        # Checking needed folders and files exists
        if not exists(cfg['LOG_DIR']):
            log().error('Folder "{0}" that should contain input nginx-log files not exists. '
                        'Please check the path in configuration file.'.format(cfg['LOG_DIR']))
            return 1
        if not exists(cfg["REPORT_DIR"]):
            log().error('Folder "{0}" for output report files not exists. '
                        'Please check the path in configuration file.'.format(cfg['REPORT_DIR']))
            return 1
        for checked_file in ['report.html', 'jquery.tablesorter.min.js', 'jquery.tablesorter.js']:
            if not isfile(join(cfg["REPORT_DIR"], checked_file)):
                log().error('Folder "{0}" for output report files doesn\'t contain {1}. '
                            'File {1} needed for report generating.'.format(cfg['REPORT_DIR'], checked_file))
                return 1

        # Looking for file to parse
        file_info = get_latest_logfile_info(cfg['LOG_DIR'])
        if not file_info.path:
            log().info('No file found to analyse.')
            return 0
        report_filename = join(cfg["REPORT_DIR"], 'report-'+str(file_info.date)+'.html')
        if exists(report_filename):
            log().info('Report for latest nginx-log file ({}) have been already done. '
                       'Check it in file {}.'.format(file_info.path, report_filename))
            return 0

        # Analysing
        log().info('Analysing file '+file_info.path)
        statistic_db = analyse_log_file(file_info.path)

        # Reporting
        report_template=join(cfg["REPORT_DIR"], 'report.html')
        generate_report(statistic_db, report_template, report_filename, cfg['REPORT_SIZE'])
        log().info('Report was generated to '+report_filename)

        return 0

    except WrongFileToParseException as ex:
        log().error(ex)
        return 1
    except Exception as ex:
        log().exception(ex)
        return 1

if __name__ == "__main__":
    main(config)
