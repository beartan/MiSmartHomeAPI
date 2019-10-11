#-*- coding:utf8 -*-
# Copyright (c) 2019 barriery
# Python release: 3.7.0
from django.http import HttpResponse, HttpResponseBadRequest

import os
import sys
import json

device_dict = {}

def device(request):
    if request.method == 'PUT':
        check = validate(request.PUT, ['localip', 'name', 'token'])
        if check is not None:
            return check
        attributes = ['name', 'token']
        obj = {attr: request.PUT[attr] for attr in attributes}
        obj['status'] = 0 # off
        localip = request.PUT['localip']
        device_dict[localip] = obj
        return HttpResponse(help())
    elif request.method == 'GET':
        return HttpResponse(json.dumps(device_dict, indent=4))
    elif request.method == 'DELETE':
        check = validate(request.DELETE, ['localip'])
        if check is not None:
            return check
        localip = request.DELETE['localip']
        if localip not in device_dict:
            return HttpResponseBadRequest("localip[%s] has been not set.\n" % localip)
        device_dict.pop(localip)
        return HttpResponse(help())
    elif request.method == 'POST':
        check = validate(request.POST, ['localip'])
        if check is not None:
            return check
        localip = request.POST['localip']
        device = device_dict.get(localip)
        if not device:
            return HttpResponseBadRequest("localip[%s] has been not set.\n" % localip)
        status_list = ['off', 'on']
        status = request.POST.get('status')
        if status not in status_list:
            device['status'] = (device['status'] + 1) % 2
            status = status_list[device['status']]
        cmd = 'miceil --ip %s --token %s %s' % (localip, device['token'], status)
        os.system(cmd)
        return HttpResponse(help())

def validate(request_method, requested):
    for key in requested:
        if not request_method.get(key):
            return HttpResponseBadRequest("Missing %s.\n"%key)
    return None

def help():
    return '''
HELP:
    GET
        - Description:  List devices infomation.
    PUT
        - Description:  Add a device. The default status of device is off.
        - Form:
            @localip    IP address of device in LAN
            @token      Device token, which is allocated when the device connects to MI-HOME app
            @name       Device name (this value is generally set in MI-HOME app)
    DELETE
        - Description:  Delete a device.
        - Form:
            @localip    IP address of device in LAN
    POST
        - Description:  Given instructions, control device(Default switch on and off status).
        - Form:
            @localip    IP address of device in LAN
            @status     on or off(not necessary)
'''
