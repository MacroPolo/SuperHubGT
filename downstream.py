#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Downstream channel graph generator.
"""

import sys
import re
import time
import os.path
import logging
import json
import collections
import argparse
import random
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

__author__ = "MacroPolo"
__copyright__ = "Copyright 2016, MacroPolo"
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "MacroPolo"
__email__ = "contact@slashtwentyfour.net"
__status__ = "Production"


def testconfig():
    """Verify that the netpulse config file can be parsed by JSON."""
    with open(config_location, 'r') as f:
        try:
            config = json.load(f)
        except:
            print 'ERROR: Failed to load JSON configuration. Please verify your', \
            'config file with a JSON validator e.g. http://jsonlint.com/'
            sys.exit(1)
    f.close
    return()


def generate_csv(field_name, filename):
    """Generate CSV files from downstream information""" 
    new_values = []
    new_values.append(str(timestamp))

    for field in field_name:
        if field != "N/A":
            new_values.append(str(field))
        else:
            new_values.append('0')

    new_values = ",".join(new_values)
    
    # Check if the file to be appended to exists. If not, create it.
    file_check = os.path.isfile('%s%s.csv' % (www_dir, filename))
    if file_check == True:
        f = open('%s%s.csv' % (www_dir, filename),'a')
        f.write(new_values + '\n')
        f.close()
        logging.info('Populated %s.csv with new data' % filename)
    else:
        f = open('%s%s.csv' % (www_dir, filename),'a')
        headers = ['Timestamp','DS-1','DS-2','DS-3','DS-4','DS-5','DS-6','DS-7','DS-8']
        headers = ",".join(headers)
        f.write(headers + '\n')
        f.write(new_values + '\n')
        f.close()
        logging.info('%s.csv has been created' % filename)
    return()


def cleancsv(filename):
    """ Delete old rows from the downstream csv files according to the 
    'data_retention' value in configuration file. To save disk writes, the delete 
    runs intermitently, based on the polling interval, rather than every call.
    """
    x = (86400/interval)
    y = x * 0.95 # old data should be deleted on approx 5% of runs per day
    z = random.randint(0,x)
    
    if z > y:
        delete_before = datetime.today() - timedelta(days=data_retention)
        logging.info('Deleting data before %s from %s' % (delete_before, filename))

        f = open('%s%s' % (www_dir, filename), 'r')
        content = f.readlines()
        f.close()

        f = open('%s%s' % (www_dir, filename), 'w')
        for line in content:
            line_delimited = line.split(',')
            if line_delimited[0] == "Timestamp":
                f.write(line)   # always keep the CSV headers
            else:
                time = datetime.strptime(line_delimited[0], "%Y-%m-%d %H:%M:%S")
                if time >= delete_before:
                    f.write(line)
        f.close()
        logging.info('Delete complete')


parser = argparse.ArgumentParser(description='Superhub Monitoring/Graphing Tool')
parser.add_argument('-t', '--configtest',  action='store_true', 
                    help='Test the JSON config file')
parser.add_argument('-c', '--config',  action='store', required=True,
                    help='Location of the config file')
args = parser.parse_args()

config_location = args.config

if args.configtest == True:
    testconfig()
    print ">>> Config OK"
    sys.exit(0)
else:
    # Retrive values from configuration file
    with open(config_location, 'r') as f:
        config = json.load(f)
    f.close

log_dir = config['logs']['log_directory']
www_dir = config['logs']['www_directory']
hub_ip = config['superhub']['ip_address']
data_retention = config['logs']['data_retention']
interval = config['downstream']['interval']

logging.basicConfig(filename='%snetpulse.log' % log_dir,
                    format='%(levelname)s: %(asctime)s %(message)s',
                    level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')

logging.info('Starting to retrieving new downstream information')

timestamp = time.time()
timestamp = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

cleancsv('downstream_power.csv')
cleancsv('downstream_rx.csv')
cleancsv('downstream_post_errors.csv')

try:
    r = requests.get('http://%s/cgi-bin/VmRouterStatusDownstreamCfgCgi' % hub_ip)
except requests.exceptions.ConnectionError:
    logging.error('Unable to connect to http://%s/cgi-bin/VmRouterStatusDownstreamCfgCgi. Is the IP address correct?' 
                  % hub_ip)
    sys.exit(1)

status = r.status_code
if status != 200:
    logging.error('Unable to connect to http://%s/cgi-bin/VmRouterStatusDownstreamCfgCgi. Got response: %s' 
                  % (hub_ip, status))
    sys.exit(1)

# Scrape the downstream information
html_data = r.text
table_data = [[cell.text for cell in row("td")]
                         for row in BeautifulSoup(html_data, "lxml")("tr")]
#frequency = table_data[1][1:]
#lock_status = table_data[2][1:]
#channel_id = table_data[3][1:]
#modulation = table_data[4][1:]
#symbol_rate = table_data[5][1:]
#interleave_depth = table_data[6][1:]
power_level = table_data[7][1:]
rxmer = table_data[8][1:]
#pre_rs_errors = table_data[9][1:]
post_rs_errors = table_data[10][1:]

logging.info('Sucessfully retrieved new downstream statistics from Super Hub')

# Generate graphs for each field that we are interested in
generate_csv(power_level, 'downstream_power')
generate_csv(rxmer, 'downstream_rx')
#generate_csv(pre_rs_errors, 'downstream_pre_errors')
generate_csv(post_rs_errors, 'downstream_post_errors')
