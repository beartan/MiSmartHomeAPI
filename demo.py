#-*- coding:utf8 -*-
# Copyright (c) 2019 barriery
# Python release: 3.7.0
import requests
import asyncio
import json

terminals = {
    'plug': '236738672',
    'light': '235388260',
    'gateway': '133638119',
    'speaker': '295339237',
    'fen': '106456356',
    'airpurifier': '288438027',
    'weather': '158d0002d798b6',
    'magnet': '158d0004318a22',
}

def get_url(terminal_str):
    base_url = 'http://localhost:8000'
    if terminal_str not in terminals:
        raise ValueError(f'{terminal_str} not in defined terminals')
    tid = terminals[terminal_str]
    return f"{base_url}/{tid}"

async def service(interval):
    print('[service] info: turn light on if humidity >= 55.0%%, interval: %ds' % interval)
    print('[service] start')
    s = requests.Session()
    while True:
        r = s.get(get_url('weather'))
        try:
            data = r.json()['data']
            temperature = float(data['temperature']) / 100.0
            humidity = float(data['humidity']) / 100.0
            print(f' temperature: {temperature}')
            print(f' humidity: {humidity}')
            if humidity >= 55.0:
                s.post(get_url('light'), data={'status': '1'})
            else:
                s.post(get_url('light'), data={'status': '0'})
        except Exception as e:
            print(e)
        await asyncio.sleep(interval)

if __name__ == '__main__':
    asyncio.run(service(5))
