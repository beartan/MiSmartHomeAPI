#-*- coding:utf8 -*-
# Copyright (c) 2019 barriery
# Python release: 3.7.0
from django.http import HttpResponse, HttpResponseBadRequest

import os
import sys
import json
import multiprocessing

from miio import ceil

from . import manager

ma = manager.DeviceManager()

def device(request, device_id=None):
    device_id = str(device_id)
    if request.method == 'PUT':
        check = validate(request.PUT, ['device_id', 'token'])
        if check is not None:
            return check
        device_id = request.PUT.get('device_id')
        attributes = ['token', 'name', 'localip', 'type']
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
        status = request.POST.get('status')
        status_list = ['off', 'on']
        if status not in status_list:
            s = (ma.get_status(device_id) + 1) % 2
            ma.set_status(device_id, s)
        else:
            if status == status_list[ma.get_status(device_id)]:
                return HttpResponse(help())
            else:
                s = (ma.get_status(device_id) + 1) % 2
                ma.set_status(device_id, s)

        device = ceil.Ceil(ma.get_localip(device_id), ma.get_token(device_id))
        if s == 1:
            device.on()
        else:
            device.off()
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
HELP:
    PUT
        - Description:  Add a device. The default status of device is off.
        - Path:
            /
        - Form:
            @device_id  Device Id
            @localip    IP address of device in LAN
            @token      Device token, which is allocated when the device connects to MI-HOME app
            @type       Device type (not necessary)
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
            @localip    IP address of device in LAN
            @status     on or off(not necessary)
'''
