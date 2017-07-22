# SuperHubGT
The Virgin Media SuperHub is a consumer grade cable modem/router combo provided 
to customers of the UK based ISP when they sign up for broadband services. Virgin 
Media offer the fastest consumer broadband in the UK however the feature set found 
on their devices has never been great, particularly when it comes to monitoring 
capabilities.

After suffering a few connection dropouts, I decided to try and put together a 
homemade monitoring tool to keep an eye on the health of the device and so 
created the "SuperHub Graphing Tool". Two Python scripts poll the SuperHub web UI 
for data, add it to csv files and then through the use of 
[Highstock](http://www.highcharts.com/), the results and graphed and displayed 
on a webpage.

I have uploaded all of the code to [Github](https://github.com/MacroPolo/SuperHubGT) 
and you can see a demo of the graphs 
[here](http://slashtwentyfour.net/demo/superhubgt/graphs.html).

![SuperHubGT_Example](https://macropolo.github.io/img/2016-11-02-superhub_gt/superhubgt_preview.png "SuperHubGT_Example")

For anyone interested in setting up this tool for themselves, the instructions 
below should walk you through everything you need, provided you have at least 
a basic grasp of Linux systems administration.

# Prerequisites 

The following will be required in order to use the code (without modifications):

* An "always-on" Linux based system where the scripts will be ran from. I will 
be using `Ubuntu Server 16.04` for this guide.
* A web server installed and configured on your system. I use `nginx` and will 
include a basic guide on how to configure that.
* SuperHub 2 (Super Hub VMDG490). I have only tested this code on a Superhub 2 
with 8 Downstream channels. I do not know whether the UI is different on 
different SuperHub models. Perhaps if someone is able to test and make a 
pull request for code changes I can add SuperHub version detection logic into 
the scripts.

**Note**: The graphs are generated through the fantastic Javascript library 
provided by [Highcharts](https://shop.highsoft.com/highstock). Highcharts is 
free for non-profit organisations or for personal use. The SuperHub is a 
consumer grade device, so I would not expect anyone to be using this tool in 
a commercial setting, but if you do, please ensure that you purchase an 
appropriate [license](https://shop.highsoft.com/highstock) from Highcharts 
before use.

# Installation

## SuperHubGT

The first step will be to download the files from the Git project into a 
suitable directory. There are two ways you can do this, either via the `git` 
command line or by downloading and unzipping the files manually.

### Option 1: Git Method

```shell
root@ubuntu:~# cd /usr/local/sbin/
root@ubuntu:/usr/local/sbin# git clone https://github.com/MacroPolo/SuperHubGT.git
```

### Option 2: Manual Method

```shell
root@ubuntu:~# cd /usr/local/sbin/
root@ubuntu:/usr/local/sbin# wget https://github.com/MacroPolo/SuperHubGT/archive/master.zip
root@ubuntu:/usr/local/sbin# unzip master.zip
```

__Note__: If `unzip` is not installed on your system, you can install it with 
`sudo apt-get update && sudo apt-get install unzip`

## Python

Depending on the version of Linux you are using, `Python 2.7` may not be 
installed on your system. Install it with 
`sudo apt-get update && sudo apt-get install python2.7`.

In addition, there are two Python modules required `requests` and `beautifulsoup` 
which can be installed in a similar manner:

```shell
sudo apt-get install python-bs4
sudo apt-get install python-requests
```

# Configuration

## Web Server (nginx)

If you already have a web server up and running on your system, all you will need 
to do is copy the contents of the `www` folder into a new directory under 
`/var/www/` and configure your web server accordingly to point to the new website.

For people without a running webserver, the following steps will get you up and 
running with a basic `nginx` configuration.

### Install nginx

```shell
sudo apt-get update && sudo apt-get install nginx
```

You should now be able to access your server through a web browser and see the 
nginx sample webpage.

### Create Directories

After `nginx` has been installed, create a new directory under `/var/www/` and 
copy the `index.html` file and `js` directory into it as follows:

```shell
root@ubuntu:~# mkdir /var/www/superhubgt
root@ubuntu:~# mv /usr/local/sbin/SuperHubGT/www/index.html /var/www/superhubgt/
root@ubuntu:~# mv /usr/local/sbin/SuperHubGT/www/js/ /var/www/superhubgt/
```

Next, we need to create two log files which nginx can write to:

```shell
root@ubuntu:~# touch /var/log/nginx/superhubgt_access.log
root@ubuntu:~# touch /var/log/nginx/superhubgt_error.log
```

### nginx Configuration

After the above steps have been completed, we can now create the nginx 
configuration file for our website and get everything up and running. The first thing you will have to do however is get rid of the default webpage that ships with nginx. To do that, simply remove the symlink from the sites-enabled directory as follows:

```shell
root@ubuntu:~# rm /etc/nginx/sites-enabled/default
```

Next, create a new configuration file in the `/etc/nginx/conf.d/` directory with
the following minimum configuration:

```shell
root@ubuntu:~# cat /etc/nginx/conf.d/superhubgt.conf
# SuperHubGT nginx configuration

server {
    listen 80;
    server_name superhubgt;

    root /var/www/superhubgt;
    index index.html;

    error_log /var/log/nginx/superhubgt_error.log;
    access_log /var/log/nginx/superhubgt_access.log;

    location / {
        try_files $uri $uri/ $uri/ =404;
    }
}
```

You can now verify your configuration to ensure `nginx` accepts it and then
restart `nginx`:

```shell
root@ubuntu:~# service nginx configtest
 * Testing nginx configuration                                                                   [ OK ]
root@ubuntu:~# service nginx restart
```

Now if you refresh your browser, you should see the skeleton of the SuperHubGT 
webpage!

## SuperHubGT Configuration

You will now need to edit the `config.json` file to tailor the scripts to your 
requirements and system. Parameters are explained the annotated config file below:

```
root@ubuntu:~# cat /usr/local/sbin/SuperHubGT/config.json
{
  "logs": {
    "log_directory": "/var/log/superhubgt/",   ## The directory where SuperHubGT will log to. Create this directory if it doesn not already exist.
    "www_directory": "/var/www/superhubgt/",   ## The website directory you created previously    
    "data_retention": 7   ## How many days of data to save and graph     
  },
  "superhub": {
    "ip_address": "192.168.0.1",   ## The IP address of your SuperHub
    "password": "password123"   ## The password for your SuperHub web UI
  },
  "bandwidth": {
    "interval": 60,   ## How often (seconds) to poll the SuperHub for Download and Upload values. This should match the cron interval (explained below).
    "enable_icmp": true,   ## Set to true if you have a Ping monitor set up on the http://www.thinkbroadband.com/ping website.
    "icmp_id": "1234567890abcd"   ## The ID of your Ping monitor graph
  },
  "downstream": {
    "interval": 60   ## How often (seconds) to poll the SuperHub for Downstream channel information. This should match the cron interval (explained below).
  }
}
```

After making the necessary changes, you can run either of the two scripts with 
the `-t` flag to check the configuration file and make sure it is valid. For 
example:

```shell
root@ubuntu:/usr/local/sbin/SuperHubGT# python bandwidth.py -c config.json -t
>>> Config OK
```

# Running the Scripts

The two scripts are executed by cron job with timers which should match the two 
`interval` values you set in the `config.json` file for bandwidth and downstream.

Example cron file:

```shell
PATH=/usr/sbin:/usr/sbin:/usr/bin:/sbin:/bin

# execute bandwidth.py every minute
* * * * * root /usr/bin/python /usr/local/sbin/SuperHubGT/bandwidth.py -c /usr/local/sbin/SuperHubGT/config.json

# execute downstream.py every 5 minutes
*/5 * * * * root /usr/bin/py
```

After saving the cron file, you should now be able to monitor the SuperHubGT log 
file for status updates. Assuming everything works as expected, you should find 
four `csv` files have been generated in your `/var/www/` directory along with 
an `icmp.png` file if you have enabled the ThinkBroadband ICMP monitor.

```shell
root@ubuntu:~# ll /var/www/superhubgt/
total 264
drwxr-xr-x 3 root root   4096 Nov  5 06:09 ./
drwxr-xr-x 4 root root   4096 Nov  5 05:10 ../
-rw-r--r-- 1 root root    240 Nov  5 06:10 bandwidth.csv
-rw-r--r-- 1 root root    209 Nov  5 06:10 downstream_post_errors.csv
-rw-r--r-- 1 root root    230 Nov  5 06:10 downstream_power.csv
-rw-r--r-- 1 root root    254 Nov  5 06:10 downstream_rx.csv
-rw-r--r-- 1 root root 221658 Nov  5 06:10 icmp.png
-rw-r--r-- 1 root root  13066 Nov  5 04:50 index.html
drwxr-xr-x 2 root root   4096 Nov  5 04:50 js/
```

Refreshing your web browser once more should now show the graphs being generated!

Hopefully the above steps have been detailed enough to get you up and running with the SuperHub Graphing Tool, however I will be happy to answer any questions or help out with configuration. Please post in the comments below or email <a href="mailto:contact@slashtwentyfour.net">contact@slashtwentyfour.net</a>.

Lastly, although I have not tested these scripts in a Windows environemnt, I 
don't think it would take too much time to alter them to work. It should also 
be possible to fairly easily add additional graphs for other parts of the 
SuperHub UI which you wish to graph.
