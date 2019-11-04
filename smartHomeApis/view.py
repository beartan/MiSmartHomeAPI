#-*- coding:utf8 -*-
# Copyright (c) 2019 barriery
# Python release: 3.7.0
from django.http import HttpResponse, HttpResponseBadRequest

import os
import sys
import json
import xiaomi_gateway
import multiprocessing

from miio import ceil

from . import manager
from . import config

ma = manager.Manager()
#  gateway_instance = xiaomi_gateway.XiaomiGateway(config.GATEWAY['localip'], config.GATEWAY['port'], config.GATEWAY['mac'], config.GATEWAY['password'], 1, 'any')

def gateway(request, sensor_sid):
    if not ma.registered(sensor_sid):
        return HttpResponseBadRequest("bad sensor sid.\n")
    info = ma.get_terminal(sensor_sid).getter('data')
    return HttpResponse(json.dumps(info))

def device(request, device_id=None):
    if isinstance(device_id, int):
        device_id = str(device_id)
    if request.method == 'PUT':
        if not device_id:
            return HttpResponseBadRequest("bad device id.\n")
        check = validate(request.PUT, ['token'])
        if check is not None:
            return check
        attributes = ['token', 'name', 'localip']
        device_param = {attr: request.PUT.get(attr) for attr in attributes}
        ma.add_device(device_id, device_param)
        return HttpResponse(ma.get_json_string(device_id))
    elif request.method == 'GET':
        return HttpResponse(ma.get_json_string(device_id))
    elif request.method == 'DELETE':
        if not ma.registered(device_id):
            return HttpResponseBadRequest("device has been not registered.\n")
        ma.delete_device(device_id)
        return HttpResponse(help())
    elif request.method == 'POST':
        if not ma.registered(device_id):
            return HttpResponseBadRequest("device has been not registered.\n")
        if ma.getter(device_id, 'inroom') == "False":
            return HttpResponseBadRequest("device not in room.\n")
        requested_params = ['localip', 'token']
        for param in requested_params:
            if not ma.getter(device_id, param):
                return HttpResponseBadRequest("the %s of the device has not been set.\n" % param)
        status = request.POST.get('status')
        ps = int(ma.getter(device_id, 'status'))
        if status is None:
            s = (ps + 1) % 2
        else:
            s = int(status)
            if s == ps:
                return HttpResponse(help())
                
        #  except miio.exceptions.DeviceException:
        device = ceil.Ceil(ma.getter(device_id, 'localip'), ma.getter(device_id, 'token'))
        if s == 1:
            device.on()
        else:
            device.off()
        ma.setter(device_id, 'status', str(s))
        return HttpResponse(help())

def validate(request_method, requested):
    for key in requested:
        if not request_method.get(key):
            return HttpResponseBadRequest("Missing %s.\n"%key)
    return None

def show_help(request):
    return HttpResponse(help())

def help():
    return '''
PUT
    - Description:  Add a device. The default status of device is off.
    - Path:
        /<int:device_id>
    - Form:
        @localip    IP address of device in LAN
        @token      Device token, which is allocated when the device connects to MI-HOME app
        @name       Device name which is generally set in MI-HOME app (not necessary)
GET
    - Description:  List devices infomation.
    - Path: 
        /                   List all devises infomation
        /<int:device_id>    List device infomation corresponding to the device_id
DELETE
    - Description:  Delete a device by device_id.
    - Path:
        /<int:device_id>
POST
    - Description:  Given instructions, control device(Default switch on and off status).
    - Path:
        /<int:device_id>
    - Form:
        @status     0 or 1(not necessary)
'''
