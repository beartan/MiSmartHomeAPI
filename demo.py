#-*- coding:utf8 -*-
# Copyright (c) 2019 barriery
# Python release: 3.7.0
import requests
import asyncio
import json
import time
import logging

_LOGGER = logging.getLogger(__name__)

terminals = {
    'plug': '236738672',
    'lamp': '235388260',
    'gateway': '133638119',
    'speaker': '295339237',
    'fan': '106456356',
    'airpurifier': '288438027',
    'humidifier': '134078488',
    'weather_ssr': '158d0002d798b6',
    'magnet_ssr': '158d0004318a22',
    'light_ssr': '04CF8CAA9715',
    'motion_ssr': '158d0003f2959f',
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
        _LOGGER.warning(r.text)
        _LOGGER.warning(e)
    return None

def get_data(terminal_str, key=None, is_sensor=True):
    ret = get(terminal_str)
    if ret is not None:
        if is_sensor:
            return ret['data'] if key is None else ret['data'].get(key)
        return ret['status']
    return None

def turn(terminal_str, data=None):
    s = requests.Session()
    s.post(get_url(terminal_str), data=data)

def seneor_operator(ssr, key, op, value):
    ops = ['<', '=', '>']
    if op not in ops:
        raise ValueError(f'{op} not in {ops}')
    data = get_data(ssr, key)
    if data is not None:
        _LOGGER.info(f'{key}: {data}')
        if not isinstance(data, type(value)):
            data = type(value)(data)
        if op == '<':
            return data < value
        elif op == '=':
            return data == value
        elif op == '>':
            return data > value
        else:
            return ValueError(f'unknown op: {op}')
    return None

async def light_service(interval):
    _LOGGER.info(f'[service] info: Turn on the lamp when the environment is dark(illumination < 1000), interval: {interval}s')
    _LOGGER.info('[service] start')
    while True:
        threshold = 1000
        if seneor_operator('light_ssr', 'illumination', '<', threshold):
            turn('lamp', data={'status': '1'})
        else:
            turn('lamp', data={'status': '0'})
        await asyncio.sleep(interval)

async def service(interval):
    while True:
        _LOGGER.info(f'\n[sleep] {interval}s')
        await asyncio.sleep(interval)
        if not seneor_operator('magnet_ssr', 'status', '=', 'open'):
            continue
        
        lux_threshold = 100
        if seneor_operator('motion_ssr', 'lux', '>', lux_threshold):
            continue
        
        illumination_threshold = 1000
        if seneor_operator('light_ssr', 'illumination', '>', illumination_threshold):
            continue

        turn('lamp', data={'status': '1'})

        temperature_thresold = 2200
        if seneor_operator('weather_ssr', 'temperature', '>', temperature_thresold):
            turn('fan', data={'status': '1'})
        else:
            turn('fan', data={'status': '0'})

        humidity_thresold = 2400
        if seneor_operator('weather_ssr', 'humidity', '<', humidity_thresold):
            turn('humidifier', data={'status': '1'})
        else:
            turn('humidifier', data={'status': '0'})

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                        datefmt='%Y-%m-%d %H:%M', level=logging.INFO)
    asyncio.run(service(5))
