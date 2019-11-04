#-*- coding:utf8 -*-
# Copyright (c) 2019 barriery
# Python release: 3.7.0

DEBUG = True

MONITOR_INTERVAL = 15
DISCOVER_TIMEOUT = 2

if DEBUG:
    MONITOR_INTERVAL = 10
    
DEVICE_TOKEN = {
    '235388260': 'eb6ce266e5a6c25cbc2515471634d2be', # 台灯
    '236738672': 'd0706b31c18bb0e7baae320a80700ece', # 插座
    '133638119': 'e1ab4a0a3e2fbc4c1501aa395fd795ec', # 网关
    # 'blt.3.10pl1psvk5800' = 'f8e25d56d909b39e6ea8ba55', # 温湿度计
}

GATEWAY = {
    'localip': '192.168.31.206',
    'port': '9898',
    'sid': '158d0002d798b6',
    'password': 'i79bq7rypjw1jkcy',
}
