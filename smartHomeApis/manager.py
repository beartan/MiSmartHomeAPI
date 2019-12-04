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
    def __init__(self, terminal_manager, database_manager, monitor_interval, discover_timeout):
        super(Monitor, self).__init__()
        self.terminal_manager = terminal_manager
        self.monitor_interval = monitor_interval
        self.discover_timeout = discover_timeout
        self.database_manager = database_manager
    def run(self):
        while True:
            sys.stdout.write(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())+'\n')
            self.monitor_devices(self.terminal_manager, self.discover_timeout)
            self.monitor_sensors(self.terminal_manager)
            sys.stdout.write(json.dumps(self.terminal_manager.copy(), indent=4)+'\n')
            if self.database_manager is not None:
                self.database_manager.push_to_database(self.terminal_manager, repeated_filter=True)
            time.sleep(self.monitor_interval)
    def monitor_sensors(self, ssr_manager):
        for mac, g_items in self.terminal_manager.gateways.items():
            gid = g_items['gid']
            can_discover = True
            if not ssr_manager.registered(gid):
                _LOGGER.warning(f"gateway[{gid}] not registered")
                can_discover = False
            elif ssr_manager.terminal(gid).getter('inroom') != 'True':
                _LOGGER.warning(f"gateway[{gid}] not in room")
                can_discover = False
            elif not isinstance(self.device_discover(1, addr=ssr_manager.terminal(gid).getter('localip')), construct.lib.containers.Container):
                _LOGGER.warning(f"gateway[{gid}] can not connect")
                can_discover = False
            seen_ssrs = []
            if can_discover:
                g = self.terminal_manager.get_instantiated_gateway(mac)
                seen_ssrs = g.discover_sensors()
                _LOGGER.info(f'seen_ssrs: {seen_ssrs}')
                for sid in seen_ssrs:
                    if not ssr_manager.registered(sid):
                        new_ssr = Sensor()
                        new_ssr.belong_gateway(g, gid)
                        new_ssr.setter('inroom', 'True')
                        new_ssr.setter('id', sid)
                        if sid in config.SENSORS:
                            new_ssr.setter('name', config.SENSORS[sid].get('name'))
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
    def monitor_devices(self, dev_manager, discover_timeout):
        seen_devs = self.device_discover(discover_timeout)
        for did in seen_devs:
            dev = seen_devs.get(did)
            if not dev_manager.registered(did):
                new_dev = Device()
                new_dev.setter('inroom', 'True')
                new_dev.setter('id', did)
                new_dev.setter('localip', dev.get('localip'))
                if did in config.DEVICES:
                    new_dev.setter('token', config.DEVICES[did].get('token'))
                    new_dev.setter('name', config.DEVICES[did].get('name'))
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
    def device_discover(self, timeout, addr=None):
        is_broadcast = addr is None
        seen_addrs = []  # type: List[str]
        if is_broadcast:
            addr = '<broadcast>'
            is_broadcast = True
            _LOGGER.info("Sending discovery to %s with timeout of %ds..",
                    addr, timeout)
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
                    _LOGGER.info("  IP %s (ID: %s) - token: %s", 
                            localip, device_id, token)
                    seen_addrs.append(localip)
                    devices[device_id] = {'localip': localip}
                    if token != '00000000000000000000000000000000' and token != 'ffffffffffffffffffffffffffffffff':
                        devices[device_id]['token'] = token
            except socket.timeout:
                if is_broadcast:
                    _LOGGER.info("Discovery done")
                return  devices # ignore timeouts on discover
            except Exception as ex:
                _LOGGER.error("error while reading discover results: %s\n" % ex)
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
                print('Value[None] is illegal')
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
            print(e)
            return None
    @staticmethod
    def get_status(localip, token):
        try:
            if miio.ceil.Ceil(localip, token).status().power == 'on':
                return '1'
        except Exception as e:
            print(e)
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
        if self.get('name') is None:
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
        data = json.loads(info.get('data'))
        if data.get('error'):
            return None
        return data
    @staticmethod
    def get_model(gateway_instance, sid):
        info = gateway_instance.get_data(sid)
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
        if self.get('name') is None:
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
                self._database_manager = database.DatabaseManager(config.DATABASE['remote_ip'], config.DATABASE['remote_usr'], config.DATABASE['remote_pwd'],
                            config.DATABASE['database_usr'], config.DATABASE['database_pwd'], config.DATABASE['database_name'])
            self._terminal_manager = TerminalManager(config.GATEWAYS, config.LOCATION)
            self._monitor = Monitor(self._terminal_manager, self._database_manager, config.MONITOR_INTERVAL, config.DISCOVER_TIMEOUT)
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
    def getter(self, tid, key):
        return self._terminal_manager.terminal(tid).getter(key)
    def setter(self, tid, key, value):
        return self._terminal_manager.terminal(tid).setter(key, value)
