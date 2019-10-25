#-*- coding:utf8 -*-
# Copyright (c) 2019 barriery
# Python release: 3.7.0
import requests
import asyncio

devices = {'chuangmi.plug.m3': '236738672',
           'yeelink.light.lamp1': '235388260'}

async def service():
    print('[service] run')
    base_url = 'http://localhost:8000/'
    plug_url = base_url + devices['chuangmi.plug.m3']
    light_url = base_url + devices['yeelink.light.lamp1']
    s = requests.Session()
    pre_plug_status = None
    while True:
        r = s.get(plug_url)
        try:
            status = r.json()['status']
            print('plug status: %d' % status)
            if pre_plug_status != status:
                pre_plug_status = status
                s.post(light_url, data={'status': status})
        except Exception as e:
            print(e)
        await asyncio.sleep(1)

if __name__ == '__main__':
    asyncio.run(service())
