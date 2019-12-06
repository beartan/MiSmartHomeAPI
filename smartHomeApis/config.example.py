#-*- coding:utf8 -*-
# Copyright (c) 2019 barriery
# Python release: 3.7.0

# Monitor configure.
MONITOR_INTERVAL = 5
DISCOVER_TIMEOUT = 5
PUSH_TO_DATABASE = False

# Location of terminals.
# This item is asked by database module.
LOCATION = 'NMB-G513'
    
# Information of devices.
# Notice that 'did' and 'token' must be provide, and if 'localip' is provided,
# the monitoring will be more reliable. For example, the fan can not be detected
# frequently, so add 'localip' to enhance the reliability of monitoring.
DEVICES = {
    '235388260': {
        'token': 'eb6ce266e5a6c25cbc2515471634d2be',
        'name': 'light',
    }, '236738672': {
        'token': 'd0706b31c18bb0e7baae320a80700ece',
        'name': 'pulg',
    }, '133638119': {
        'token': 'e1ab4a0a3e2fbc4c1501aa395fd795ec',
        'name': 'gateway',
    }, '295339237': {
        'token': '474c666a79446773666b7a666154414a',
        'name': 'speaker',
    }, '106456356': {
        'token': '545f0fd5b615192b39d22f526045b7fd',
        'name': 'fan',
        'localip': '192.168.31.61', # add for enhancing reliability of monitoring
    }, '288438027': {
        'token': '08f20c812846082502ecb77735f85f3e',
        'name': 'airpurifier',
    }, '134078488': {
        'token': 'a44640db2d0eb407378003d1bfb22936',
        'name': 'humidifier',
    },
}

# Information of sensors.
# This item is not neccessary, unless you want to set the 'name'. You may need
# to attention that different sensors have different data update intervals. For
# example, 'weather' updates every 10 seconds, while 'magnet' updates every seconds.
SENSORS = {
    '158d0002d798b6': {
        'name': 'weather',
    }, '158d0004318a22': {
        'name': 'magnet',
    }, '04CF8CAA9715': {
        'name': 'light'
    },
}

# Information of gateways.
# You must configure it if you have sensors. Every params in this item is neccessary,
# and pay attention that the value of param 'did' must match the one in DEVICES item.
GATEWAYS = {
    '04CF8CAA9715': {
        'localip': '192.168.31.206',
        'port': '9898',
        'did': '133638119',
        'password': 'i79bq7rypjw1jkcy',
    },
}

# Information of database and remote server.
DATABASE = {
    'remote_ip': '*.*.*.*',
    'remote_usr': 'barriery',
    'remote_pwd': 'the password of barriery',
    'database_usr': 'root',
    'database_pwd': 'password', 
    'database_name': 'database',
}
