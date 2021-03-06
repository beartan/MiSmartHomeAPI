import binascii
import codecs
import construct
import copy
import json
import logging
import socket
import sys
import time
import threading

import miio
import xiaomi_gateway

from . import config
from . import database

_LOGGER = logging.getLogger(__name__)

class Monitor(threading.Thread):
    def __init__(self, terminal_manager, database_manager,
            device_infos, sensor_infos, monitor_interval,
            discover_timeout, simple_output=False):
        super(Monitor, self).__init__()
        self.terminal_manager = terminal_manager
        self.monitor_interval = monitor_interval
        self.discover_timeout = discover_timeout
        self.database_manager = database_manager
        self.device_infos = device_infos
        self.sensor_infos = sensor_infos
        self.simple_output = simple_output
    def monitor_log(self):
        _LOGGER.info(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        if self.simple_output:
            temp_terminals = {}
            for t, params in self.terminal_manager.copy().items():
                if params.get('inroom') == 'True':
                    name = params.get('name')
                    temp_terminals[name] = params['data'] if params['type'] == 'Sensor' else params['status']
            _LOGGER.info(json.dumps(temp_terminals, indent=4))
        else:
            _LOGGER.info(json.dumps(self.terminal_manager.copy(), indent=4))
        dev_total, dev_inroom = 0, 0
        ssr_total, ssr_inroom = 0, 0
        for tid, terminal in self.terminal_manager.items():
            if terminal.is_device():
                dev_total += 1
                if terminal.getter('inroom') == 'True':
                    dev_inroom += 1
            elif terminal.is_sensor():
                ssr_total += 1
                if terminal.getter('inroom') == 'True':
                    ssr_inroom += 1
        _LOGGER.info(f'DEVICE - inroom: {dev_inroom}, outroom: {dev_total-dev_inroom}, total: {dev_total}')
        _LOGGER.info(f'SENSOR - inroom: {ssr_inroom}, outroom: {ssr_total-ssr_inroom}, total: {ssr_total}')
        _LOGGER.info(f'ALL - inroom: {dev_inroom+ssr_inroom}, outroom: {dev_total+ssr_total-dev_inroom-ssr_inroom} total: {dev_total+ssr_total}')
        if ssr_inroom == 0 and ssr_total != 0:
            _LOGGER.warning('Can not discover any sensor, maybe all gateways are out of contact.')
        if ssr_inroom + dev_inroom == 0:
            _LOGGER.warning('Can not discover any device or sensor, maybe you are in a different LAN.')
    def run(self):
        while True:
            self.monitor_devices(self.terminal_manager, self.device_infos, self.discover_timeout)
            self.monitor_sensors(self.terminal_manager, self.sensor_infos)
            self.monitor_log()
            if self.database_manager is not None:
                self.database_manager.push_to_database(self.terminal_manager, repeated_filter=True)
                _LOGGER.info('Push to database successful')
            time.sleep(self.monitor_interval)
    def monitor_sensors(self, ssr_manager, ssr_infos):
        for mac, g_items in self.terminal_manager.gateways.items():
            gid = g_items['gid']
            can_discover = True
            if not ssr_manager.registered(gid):
                _LOGGER.warning(f"Gateway<{gid}> not registered")
                can_discover = False
            elif ssr_manager.terminal(gid).getter('inroom') != 'True':
                _LOGGER.warning(f"Gateway<{gid}> not in room")
                can_discover = False
            elif not self.is_device_inroom(ssr_manager.terminal(gid).getter('localip')):
                _LOGGER.warning(f"Gateway<{gid}> can not connect")
                can_discover = False
            seen_ssrs = []
            if can_discover:
                g = self.terminal_manager.get_instantiated_gateway(mac)
                seen_ssrs = g.discover_sensors()
                if seen_ssrs:
                    for sid in seen_ssrs:
                        if not ssr_manager.registered(sid):
                            new_ssr = Sensor()
                            new_ssr.belong_gateway(g, gid)
                            new_ssr.setter('inroom', 'True')
                            new_ssr.setter('id', sid)
                            if sid in ssr_infos:
                                new_ssr.setter('name', ssr_infos[sid].get('name'))
                            new_ssr.update()
                            ssr_manager.add(sid, new_ssr)
                        else:
                            old_ssr = ssr_manager.terminal(sid)
                            if old_ssr.getter('inroom') != 'True':
                                old_ssr.setter('inroom', 'True')
                            old_ssr.update()
            for sid in ssr_manager:
                if ssr_manager.is_sensor(sid) and sid not in seen_ssrs:
                    if ssr_manager.terminal(sid).is_belong_gateway(gid):
                        ssr_manager.terminal(sid).setter('inroom', 'False')
    def monitor_devices(self, dev_manager, dev_infos, discover_timeout):
        seen_devs = self.device_discover(discover_timeout)
        for did in seen_devs:
            dev = seen_devs.get(did)
            if not dev_manager.registered(did):
                new_dev = Device()
                new_dev.setter('inroom', 'True')
                new_dev.setter('id', did)
                new_dev.setter('localip', dev.get('localip'))
                if did in dev_infos:
                    params = dev_infos[did]
                    new_dev.setter('token', params.get('token'))
                    new_dev.setter('name', params.get('name'))
                if dev.get('token'):
                    new_dev.setter('token', dev.get('token'))
                new_dev.update()
                dev_manager.add(did, new_dev)
            else:
                old_dev = dev_manager.terminal(did)
                if old_dev.getter('localip') != dev.get('localip'):
                    old_dev.setter('localip', dev.get('localip'))
                if dev.get('token') and dev.get('token') != old_dev.getter('token'):
                    old_dev.setter('token', dev.get('token'))
                if old_dev.getter('inroom') != "True":
                    old_dev.setter('inroom', "True")
                old_dev.update()
        for did in dev_manager:
            if dev_manager.is_device(did) and did not in seen_devs:
                dev_manager.terminal(did).setter('inroom', "False")
        # check device be in the configure-file
        for did, params in dev_infos.items():
            if not dev_manager.registered(did):
                if params.get('localip') is None:
                    name = params.get('name')
                    _LOGGER.warning(f'did<{did}>[name: {name}] not discovered. Pls provide the localip.')
                    continue
                if not self.is_device_inroom(params.get('localip')):
                    continue
                new_dev = Device()
                new_dev.setter('id', did)
                new_dev.setter('token', params.get('token'))
                new_dev.setter('name', params.get('name'))
                new_dev.setter('localip', params.get('localip'))
                new_dev.setter('inroom', 'True')
                new_dev.update()
                dev_manager.add(did, new_dev)
            else:
                old_dev = dev_manager.terminal(did)
                if old_dev.getter('inroom') != 'True' and self.is_device_inroom(old_dev.getter('localip')):
                    _LOGGER.info('%s is in room, but not discovered.' % old_dev.getter('name'))
                    old_dev.update()
                    dev_manager.terminal(did).setter('inroom', 'True')
    def is_device_inroom(self, addr):
        timeout = 1
        obj = self.device_discover(timeout, addr=addr)
        return isinstance(obj, construct.lib.containers.Container)
    def device_discover(self, timeout, addr=None):
        is_broadcast = addr is None
        seen_addrs = []  # type: List[str]
        if is_broadcast:
            addr = '<broadcast>'
            is_broadcast = True
            _LOGGER.info(f"Sending discovery to {addr} with timeout of {timeout}s..")
        # magic, length 32
        helobytes = bytes.fromhex(
            '21310020ffffffffffffffffffffffffffffffffffffffffffffffffffffffff')
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(timeout)
        s.sendto(helobytes, (addr, 54321))
        devices = {}
        while True:
            try:
                data, addr = s.recvfrom(1024)
                m = miio.protocol.Message.parse(data)  # type: Message
                if not is_broadcast:
                    return m

                if addr[0] not in seen_addrs:
                    device_id = str(int(binascii.hexlify(m.header.value.device_id).decode(), 16))
                    localip = addr[0]
                    token = codecs.encode(m.checksum, 'hex').decode()
                    _LOGGER.info(f"  IP {localip} (ID: {device_id}) - token: {token}") 
                    seen_addrs.append(localip)
                    devices[device_id] = {'localip': localip}
                    if token not in ['00000000000000000000000000000000', 'ffffffffffffffffffffffffffffffff']:
                        devices[device_id]['token'] = token
            except socket.timeout:
                if is_broadcast:
                    _LOGGER.info("Discovery done")
                return  devices # ignore timeouts on discover
            except Exception as ex:
                _LOGGER.error("error while reading discover results: %s" % ex)
                break

class TerminalManager(dict):
    def __init__(self, defined_gateways, location):
        super(TerminalManager, self).__init__()
        self.lock = threading.Lock()
        self.gateways = {}
        self.location = location
        for mac, params in defined_gateways.items():
            self.gateways[mac] = {
                'instance': None,
                'gid': params['did'],
                'params': params,
            }
    def get_instantiated_gateway(self, mac):
        if self.gateways[mac]['instance'] is not None:
            return self.gateways[mac]['instance']
        with self.lock:
            params = self.gateways[mac]['params']
            self.gateways[mac]['instance'] = \
                    xiaomi_gateway.XiaomiGateway(params['localip'], params['port'], mac, params['password'], 1, 'any')
            return self.gateways[mac]['instance']
    def add(self, tid, terminal):
        with self.lock:
            self[tid] = terminal
    def terminal(self, tid):
        with self.lock:
            if not self.registered(tid):
                return None
            return self[tid]
    def registered(self, tid):
        return tid in self
    def delete(self, tid):
        with self.lock:
            self.pop(tid)
    def is_device(self, tid):
        with self.lock:
            return self[tid].is_device()
    def is_sensor(self, tid):
        with self.lock:
            return self[tid].is_sensor()

class Terminal(dict):
    def __init__(self):
        super(dict, self).__init__()
        self.lock = threading.Lock()
        keys = ['id', 'inroom', 'localip', 'token', 'type', 'model', 'name', 'status', 'data']
        for key in keys:
            self[key] = None
    def getter(self, key):
        with self.lock:
            return self[key]
    def setter(self, key, value):
        with self.lock:
            if key not in self:
                return False
            if value is None:
                _LOGGER.warning(f'{key}<{value}> is illegal')
                return False
            self[key] = value
        return True
    def type(self):
        with self.lock:
            return self['type']
    def is_device(self):
        return self.type() == 'Device'
    def is_sensor(self):
        return self.type() == 'Sensor'

class Device(Terminal):
    def __init__(self):
        super(Device, self).__init__()
        self['type'] = 'Device'
    @staticmethod
    def get_model(localip, token):
        try:
            return miio.ceil.Ceil(localip, token).info().__str__().split()[0]
        except Exception as e:
            _LOGGER.error('%s' % e)
            return None
    @staticmethod
    def get_status(localip, token):
        try:
            #  if miio.ceil.Ceil(localip, token).status().power == 'on':
                #  return '1'

            # Status not worked for AirHumidifier CA1t 
            # see: https://github.com/rytilahti/python-miio/issues/383
            power = miio.ceil.Ceil(localip, token).send("get_prop", ['power'])[0]
            if power == 'on':
                return '1'
        except Exception as e:
            _LOGGER.error('%s' % e)
        return '0'
    def update_model(self):
        localip = self.getter('localip')
        token = self.getter('token')
        if localip is None or token is None:
            return False
        if self.getter('model') is not None:
            return False
        self.setter('model', Device.get_model(localip, token))
        return True
    def update_status(self):
        localip = self.getter('localip')
        token = self.getter('token')
        if localip is None or token is None:
            return False
        self.setter('status', Device.get_status(localip, token))
        return True
    def update(self):
        self.update_model()
        self.update_status()
        if self.getter('name') is None and self.getter('model') is not None:
            self.setter('name', self.getter('model'))

class Sensor(Terminal):
    def __init__(self):
        super(Sensor, self).__init__()
        self.belong = None
        self.belong_gid = None
        self['type'] = 'Sensor'
    def belong_gateway(self, g, gid):
        with self.lock:
            self.belong = g
            self.belong_gid = gid
    def is_belong_gateway(self, gid):
        with self.lock:
            return self.belong_gid == gid
    @staticmethod
    def get_data(gateway_instance, sid):
        info = gateway_instance.get_data(sid)
        if info is None:
            return None
        data = json.loads(info.get('data'))
        if data.get('error'):
            return None
        return data
    @staticmethod
    def get_model(gateway_instance, sid):
        info = gateway_instance.get_data(sid)
        if info is None:
            return None
        return info.get('model')
    def update_data(self):
        gateway = self.belong
        sid = self.getter('id')
        if gateway is None or sid is None:
            return False
        self.setter('data', Sensor.get_data(gateway, sid))
        return True
    def update_model(self):
        gateway = self.belong
        sid = self.getter('id')
        if gateway is None or sid is None:
            return False
        self.setter('model', Sensor.get_model(gateway, sid))
        return True
    def update(self):
        self.update_data()
        self.update_model()
        if self.getter('name') is None and self.getter('model') is not None:
            self.setter('name', self.getter('model'))

class Manager(object):
    _instance = None
    _monitor = None
    _terminal_manager = None
    def __new__(self, *args, **kw):
        if not self._instance:
            self._instance = super(Manager, self).__new__(self, *args, **kw)
        return self._instance
    def __init__(self):
        if not self._monitor:
            self._database_manager = None
            if config.PUSH_TO_DATABASE:
                self._database_manager = database.DatabaseManager(config.DATABASE['remote_ip'], config.DATABASE['remote_usr'],
                                                                  config.DATABASE['remote_pwd'], config.DATABASE['database_usr'],
                                                                  config.DATABASE['database_pwd'], config.DATABASE['database_name'])
            self._terminal_manager = TerminalManager(config.GATEWAYS, config.LOCATION)
            self._monitor = Monitor(self._terminal_manager, self._database_manager,
                                    config.DEVICES, config.SENSORS,
                                    config.MONITOR_INTERVAL, config.DISCOVER_TIMEOUT, config.SIMPLE_OUTPUT)
            self._monitor.daemon = True
            self._monitor.start()
    def add_device(self, did, params):
        if not self.registered(did):
            new_dev = Device()
            for key, value in params.items():
                new_dev.setter(key, value)
            new_dev.setter('inroom', "False")
            new_dev.update()
            self._terminal_manager.add(did, new_dev)
        else:
            old_dev = self._terminal_manager.terminal(did)
            if params.get('token') and params.get('token') != old_dev.getter('token'):
                old_dev.setter('token', params.get('token'))
                old_dev.update()
            if params.get('name'):
                old_dev.setter('name', params.get('name'))
    def get_terminal(self, tid=None):
        if self.registered(tid):
            if self.is_inroom(tid):
                self.update_sensor(tid)
            return self._terminal_manager.terminal(tid)
        return self._terminal_manager
    def get_json_string(self, tid=None, indent=4):
        return json.dumps(self.get_terminal(tid), indent=indent)
    def delete_device(self, did):
        if not self.registered(did):
            return False
        self._terminal_manager.delete(did)
        return True
    def registered(self, tid):
        return self._terminal_manager.registered(tid)
    def is_inroom(self, tid):
        return self.getter(tid, 'inroom') == 'True'
    def update_sensor(self, sid):
        if self.is_sensor(sid):
            self._terminal_manager.terminal(sid).update()
    def is_sensor(self, tid):
        return self._terminal_manager.terminal(tid).is_sensor()
    def is_device(self, tid):
        return self._terminal_manager.terminal(tid).is_device()
    def getter(self, tid, key):
        return self._terminal_manager.terminal(tid).getter(key)
    def setter(self, tid, key, value):
        return self._terminal_manager.terminal(tid).setter(key, value)
