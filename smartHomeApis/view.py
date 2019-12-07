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

def manager(request, tid=None):
    if request.method == 'PUT':
        if not tid:
            return HttpResponseBadRequest("bad device id.\n")
        check = validate(request.PUT, ['token'])
        if check is not None:
            return check
        attributes = ['token', 'name', 'localip']
        device_param = {attr: request.PUT.get(attr) for attr in attributes}
        ma.add_device(tid, device_param)
        return HttpResponse(ma.get_json_string(tid))
    elif request.method == 'GET':
        if tid is not None and not ma.registered(tid):
            return HttpResponseBadRequest("terminal not registered.\n")
        return HttpResponse(ma.get_json_string(tid))
    elif request.method == 'DELETE':
        if not ma.registered(tid):
            return HttpResponseBadRequest("device has been not registered.\n")
        ma.delete_device(tid)
        return HttpResponse(help_str())
    elif request.method == 'POST':
        if not ma.registered(tid):
            return HttpResponseBadRequest("device has been not registered.\n")
        if not ma.is_inroom(tid):
            return HttpResponseBadRequest("device not in room.\n")
        requested_params = ['localip', 'token']
        for param in requested_params:
            if not ma.getter(tid, param):
                return HttpResponseBadRequest("the %s of the device has not been set.\n" % param)
        status = request.POST.get('status')
        ps = int(ma.getter(tid, 'status'))
        if status is None:
            s = (ps + 1) % 2
        else:
            s = int(status)
            if s == ps:
                return HttpResponse(help_str())

        #TODO: control device by a manager instead of control it directly
        device = ceil.Ceil(ma.getter(tid, 'localip'), ma.getter(tid, 'token'))
        if s == 1:
            device.on()
        else:
            device.off()
        ma.setter(tid, 'status', str(s))
        return HttpResponse(help_str())

def validate(request_method, requested):
    for key in requested:
        if not request_method.get(key):
            return HttpResponseBadRequest("Missing %s.\n"%key)
    return None

def help(request):
    return HttpResponse(help_str())

def help_str():
    return '''
PUT
    - Description:  Add a device.
    - Path:
        /<str:did>
    - Form:
        @localip    IP address of device in LAN
        @token      Device token, which is allocated when the device connects to MI-HOME app
        @name       Device name which is generally set in MI-HOME app (not necessary)
GET
    - Description:  List terminals(include devices and sensors) infomation.
    - Path: 
        /           List all terminals infomation
        /<int:tid>  List terminal infomation corresponding to the tid
DELETE
    - Description:  Delete a terminal by tid.
    - Path:
        /<int:tid>
POST
    - Description:  Given instructions, control device(Default switch on and off status).
    - Path:
        /<int:did>
    - Form:
        @status     0 or 1(not necessary)
'''
