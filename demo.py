#-*- coding:utf8 -*-
# Copyright (c) 2019 barriery
# Python release: 3.7.0
import requests
import asyncio
import json

terminals = {'chuangmi.plug.m3': '236738672',
           'yeelink.light.lamp1': '235388260',
           'weather.v1': '158d0002d798b6'}
async def service(interval):
    print('[service] info: turn light on if humidity >= 55.0%%, interval: %ds' % interval)
    print('[service] start')
    base_url = 'http://localhost:8000/'
    light_url = base_url + terminals['yeelink.light.lamp1']
    weather_url = base_url + terminals['weather.v1']
    s = requests.Session()
    while True:
        r = s.get(weather_url)
        try:
            data = r.json()['data']
            temperature = float(data['temperature']) / 100.0
            humidity = float(data['humidity']) / 100.0
            print(' temperature: %f' % temperature)
            print(' humidity: %f' % humidity)
            if humidity >= 55.0:
                s.post(light_url, data={'status': '1'})
            else:
                s.post(light_url, data={'status': '0'})
        except Exception as e:
            print(e)
        await asyncio.sleep(interval)

if __name__ == '__main__':
    asyncio.run(service(5))
