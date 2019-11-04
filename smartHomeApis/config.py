#-*- coding:utf8 -*-
# Copyright (c) 2019 barriery
# Python release: 3.7.0

DEBUG = True

MONITOR_INTERVAL = 15
DISCOVER_TIMEOUT = 2

if DEBUG:
    MONITOR_INTERVAL = 5
    
DEVICES = {
    '235388260': {
        'token': 'eb6ce266e5a6c25cbc2515471634d2be',
        'name': 'light',
    },
    '236738672': {
        'token': 'd0706b31c18bb0e7baae320a80700ece',
        'name': 'pulg',
    },
    '133638119': {
        'token': 'e1ab4a0a3e2fbc4c1501aa395fd795ec',
        'name': 'gateway',
    },
}

SENSORS = {
    '158d0002d798b6': {
        'name': 'Aqara_weather_sensor'
    },
}

GATEWAYS = {
    '04CF8CAA9715': {
        'localip': '192.168.31.206',
        'port': '9898',
        'mac': '04CF8CAA9715',
        'password': 'i79bq7rypjw1jkcy',
    },
}

DATABASE = {
    'remote_ip': '39.104.154.79',
    'remote_usr': 'wangch',
    'remote_pwd': '20191104wc',
    'database_usr': 'root',
    'database_pwd': '20191104', 
    'database_name': 'node_infos',
}
