#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Bandwidth graph generator.
"""

import sys
import re
import time
import os.path
import logging
import json
import shutil
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


def cleancsv():
    """ Delete old rows from the bandwidth.csv file according to the 
    'data_retention' value in configuration file. To save disk writes, the delete 
    runs intermitently, based on the polling interval, rather than every call.
    """
    x = (86400/interval)
    y = x * 0.95 # old data should be deleted on approx 5% of runs per day
    z = random.randint(0,x)
    
    if z > y:
        delete_before = datetime.today() - timedelta(days=data_retention)
        logging.info('Deleting data before %s from CSV' % delete_before)

        f = open('%sbandwidth.csv' % www_dir, 'r')
        content = f.readlines()
        f.close()

        f = open('%sbandwidth.csv' % www_dir, 'w')
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
data_retention = config['logs']['data_retention']
hub_ip = config['superhub']['ip_address']
hub_pwd = config['superhub']['password']
interval = config['bandwidth']['interval']
enable_icmp = config['bandwidth']['enable_icmp']
icmp_id = config['bandwidth']['icmp_id']

logging.basicConfig(filename='%snetpulse.log' % log_dir,
                    format='%(levelname)s: %(asctime)s %(message)s',
                    level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')

logging.info('Starting to retrieving new bandwidth information')

timestamp = time.time()
timestamp = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

cleancsv()

headers = {'Referer': 'http://%s/VmLogin.html' % hub_ip}
try:
    r = requests.get('http://%s/device_connection_status.html' % hub_ip)
except requests.exceptions.ConnectionError:
    logging.error('Unable to connect to http://%s/device_connection_status.html. Is the IP address correct?' 
                  % hub_ip)
    sys.exit(1)
    
status = r.status_code
if status != 200:
    logging.error('Unable to connect to http://%s/device_connection_status.html. Got response: %s' 
                  % (hub_ip, status))
    sys.exit(1)

# Login to Super Hub web UI
field_name = re.findall('(?<=name\=\")[]a-zA-z]{10}', r.text)
auth = dict([(str(field_name[0]), hub_pwd)])
r = requests.post('http://%s/cgi-bin/VmLoginCgi' % hub_ip, headers=headers, 
                  data=auth)
r = requests.get('http://%s/device_connection_status.html' % hub_ip)

status = r.status_code
if status != 200:
    logging.error('Unable to login to Superhub. Got response: %s' % status)
    sys.exit(1)

# Scrape the current download and upload totals
updown_total = re.findall('[0-9,]+(?=\sMB)', r.text)
download_total = int(updown_total[0].replace(",", ""))
upload_total =  int(updown_total[1].replace(",", ""))
#uptime = re.findall('[0-9]*day\s[0-9]*h\:[0-9]*m\:[0-9]*s',r.text)
#wan_ip = re.findall('(?<=\>)[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', r.text)

logging.info('Sucessfully retrieved new bandwidth information from Super Hub')

# Get the previous download and upload totals
file_check = os.path.isfile('%sbandwidth.csv' % www_dir)
if file_check == True:
    with open('%sbandwidth.csv' % www_dir, 'r') as f:
        content = f.readlines()
        for i, line in enumerate(content):
            if (i+1) == len(content):
                line_delimited = line.split(',')
                download_previous = int(line_delimited[3])
                upload_previous = int(line_delimited[4])
        f.close()

else:
    # The bandwidth.csv file has not been created yet. Lets do that now.
    headers = ['Timestamp','Download','Upload','Download_Total','Upload_Total',
               'Download_Interval','Upload_Interval']
    headers = ",".join(headers)
    new_values = [str(timestamp),'0.0','0.0',str(download_total),
                  str(upload_total),'0','0']
    new_values = ",".join(new_values)
    f = open('%sbandwidth.csv' % www_dir, 'a')
    f.write(headers + '\n')
    f.write(new_values + '\n')
    f.close()
    logging.info('bandwidth.csv has been created')
    sys.exit(0)

download_interval = download_total - download_previous
upload_interval = upload_total - upload_previous

# The upload/download values have probably been reset on the Superhub
# Lets just use the total values for bandwidth calculations
if download_interval < 0:
    download_interval = download_total
    upload_interval = upload_total
    logging.warning('Download total is less than it was previously.')

# Calculate average bandwidth values (Mbit/s)
# 1MB/s == 1,000,000 Bytes/s == 8,000,000 bits/s == 8Mbit/s
download_bandwidth = (float(download_interval)/interval) * 1000000 * 8 / 1000000
upload_bandwidth = (float(upload_interval)/interval) * 1000000 * 8 / 1000000

# Populate bandwidth.csv with the new values
new_values = [str(timestamp),str(download_bandwidth),str(upload_bandwidth),
              str(download_total),str(upload_total),str(download_interval),
              str(upload_interval)]
new_values = ",".join(new_values)

f = open('%sbandwidth.csv' % www_dir,'a')
f.write(new_values + '\n')
f.close()

# Logout of Super Hub
r = requests.get('http://%s/VmLogout2.html' % hub_ip)

logging.info('Populated bandwidth.csv with new data')

if enable_icmp == True:
    logging.info('Fetching latest ICMP graph from www.thinkbroadband.com')

    r = requests.get('http://www.thinkbroadband.com/ping/share-large/%s.png' 
                     % icmp_id, stream=True)
    status = r.status_code
    if status != 200:
        logging.error('Unable to download http://www.thinkbroadband.com/ping/share-large/%s.png' 
                      % icmp_id)
        sys.exit(1)

    with open('%sicmp.png' % www_dir, 'wb') as out_icmp:
        r.raw.decode_content = True
        shutil.copyfileobj(r.raw, out_icmp)
        out_icmp.close()
        
    logging.info('Saved latest ICMP graph')
