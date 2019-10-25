#-*- coding:utf8 -*-
# Copyright (c) 2019 barriery
# Python release: 3.7.0

DEBUG = True

MONITOR_INTERVAL = 30
DISCOVER_TIMEOUT = 2

DEVICE_TOKEN = {}

if DEBUG:
    MONITOR_INTERVAL = 3
    DEVICE_TOKEN['235388260'] = 'eb6ce266e5a6c25cbc2515471634d2be' # 台灯
    DEVICE_TOKEN['236738672'] = 'd0706b31c18bb0e7baae320a80700ece' # 插座
    DEVICE_TOKEN['133638119'] = 'e1ab4a0a3e2fbc4c1501aa395fd795ec' # 网关
    DEVICE_TOKEN['blt.3.10pl1psvk5800'] = 'f8e25d56d909b39e6ea8ba55' # 温湿度计
