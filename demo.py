#-*- coding:utf8 -*-
# Copyright (c) 2019 barriery
# Python release: 3.7.0
import requests
import asyncio
import json
import time

terminals = {
    'plug': '236738672',
    'lamp': '235388260',
    'gateway': '133638119',
    'speaker': '295339237',
    'fan': '106456356',
    'airpurifier': '288438027',
    'weather_ssr': '158d0002d798b6',
    'magnet_ssr': '158d0004318a22',
    'light_ssr': '04CF8CAA9715',
}

def get_url(terminal_str):
    base_url = 'http://localhost:8000'
    if terminal_str not in terminals:
        raise ValueError(f'{terminal_str} not in defined terminals')
    tid = terminals[terminal_str]
    return f"{base_url}/{tid}"

def get(terminal_str):
    s = requests.Session()
    r = s.get(get_url(terminal_str))
    try:
        return r.json()
    except Exception as e:
        print(e)
    return None

def turn(terminal_str, data=None):
    s = requests.Session()
    s.post(get_url(terminal_str), data=data)

async def service(interval):
    print(f'[service] info: Turn on the lamp when the environment is dark(illumination < 1000), interval: {interval}s')
    print('[service] start')
    while True:
        ret = get('light_ssr')
        if ret is not None:
            data = ret['data']
            illumination = data['illumination']
            print(f' illumination: {illumination}')
            if illumination < 1000:
                turn('lamp', data={'status': '1'})
            else:
                turn('lamp', data={'status': '0'})
        await asyncio.sleep(interval)

if __name__ == '__main__':
    asyncio.run(service(1))
