import sys
import time
import json
import copy
import miio
import socket
import binascii
import codecs
from multiprocessing import Process, Manager

from . import global_config

def discover(timeout, addr=None):
    is_broadcast = addr is None
    seen_addrs = []  # type: List[str]
    if is_broadcast:
        addr = '<broadcast>'
        is_broadcast = True
        sys.stdout.write("Sending discovery to %s with timeout of %ds..\n" %
                     (addr, timeout))
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
            #  print("Got a response: %s" % m)
            if not is_broadcast:
                return m

            if addr[0] not in seen_addrs:
                device_id = str(int(binascii.hexlify(m.header.value.device_id).decode(), 16))
                localip = addr[0]
                token = codecs.encode(m.checksum, 'hex').decode()
                sys.stdout.write("  IP %s (ID: %s) - token: %s\n" %
                             (localip, device_id, token))
                seen_addrs.append(localip)
                devices[device_id] = {'localip': localip}
                if token != '00000000000000000000000000000000' and token != 'ffffffffffffffffffffffffffffffff':
                    devices[device_id]['token'] = token
        except socket.timeout:
            if is_broadcast:
                sys.stdout.write("Discovery done\n")
            return  devices # ignore timeouts on discover
        except Exception as ex:
            sys.stderr.write("error while reading discover results: %s\n" % ex)
            break

def monitor_process(devices, discover_timeout, monitor_interval):
    sleep_time = max(0, monitor_interval - discover_timeout)
    while True:
        sys.stdout.write(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())+'\n')
        seen_devices = discover(discover_timeout)
        for Id in seen_devices:
            dev = seen_devices.get(Id)
            if Id not in devices:
                dev['inroom'] = 1
                dev['status'] = 0
                devices[Id] = dev
            else:
                if devices[Id].get('localip') != dev.get('localip'):
                    modify_manager_dict(devices, Id, 'localip', dev.get('localip'))
                if dev.get('token') and dev.get('token') != devices[Id].get('token'):
                    modify_manager_dict(devices, Id, 'token', dev.get('token'))
                if devices[Id].get('inroom') != 1:
                    modify_manager_dict(devices, Id, 'inroom', 1)
                    if devices[Id].get('token') and not devices[Id].get('type'):
                        temp = DeviceManager.get_device_type(devices[Id].get('localip'), devices[Id].get('token'))
                        if temp is None:
                            modify_manager_dict(devices, Id, 'token', None)
                        else:
                            modify_manager_dict(devices, Id, 'type', temp)
        for Id in devices.keys():
            if Id not in seen_devices:
                modify_manager_dict(devices, Id, 'inroom', 0)
        sys.stdout.write(json.dumps(devices.copy(), indent=4)+'\n')
        time.sleep(sleep_time)

def modify_manager_dict(mdict, key, attr, value):
    temp = mdict.get(key)
    temp[attr] = value
    mdict[key] = temp

class DeviceManager(object):
    '''
    _device = {
        device_id:
           {token, localip, name, status, inroom}
    }
    '''
    _instance = None
    _process = None
    _device = None
    
    def __new__(self, *args, **kw):
        if not self._instance:
            self._instance = super(DeviceManager, self).__new__(self, *args, **kw)
            def gen_get_attr_func(attr):
                def get_attr_func(self, device_id):
                    return self._device.get(device_id).get(attr)
                return get_attr_func
            def gen_set_attr_func(attr):
                def set_attr_func(self, device_id, attr_value):
                    if not self._device.get(device_id):
                        return False
                    modify_manager_dict(self._device, device_id, attr, attr_value)
                    return True
                return set_attr_func
            attr_list = ['token', 'localip', 'name', 'status', 'inroom', 'type']
            for attr in attr_list:
                setattr(self, 'get_%s' % attr, gen_get_attr_func(attr))
                setattr(self, 'set_%s' % attr, gen_set_attr_func(attr))
        return self._instance
    
    def __init__(self):
        if not self._process:
            self._device = Manager().dict()
            discover_timeout = global_config.DISCOVER_TIMEOUT
            monitor_interval = global_config.MONITOR_INTERVAL
            self._process = Process(target=monitor_process, args=(self._device, discover_timeout, monitor_interval))
            self._process.daemon = True
            self._process.start()

    @staticmethod
    def get_device_type(localip, token):
        try:
            return miio.ceil.Ceil(localip, token).info().__str__().split()[0]
        except Exception as e:
            print(e)
            return None

    #  def add_device(self, device_id, token, localip=None, name=None):
    def add_device(self, device_id, device_param):
        if not self.registered(device_id):
            self._device[device_id] = copy.deepcopy(device_param)
            self.set_status(device_id, 0)
            self.set_inroom(device_id, 0)
            #  self.set_type(device_id, miio.ceil.Ceil(self.get_localip(device_id), self.get_token(device_id)).info().__str__().split()[0])
        else:
            if device_param.get('token') and device_param.get('token') != self.get_token(device_id):
                self.set_token(device_id, device_param['token'])
                temp = self.get_device_type(self.get_localip(device_id), self.get_token(device_id))
                if temp is None:
                    self.set_token(device_id, None)
                else:
                    self.set_type(device_id, temp)
            if device_param.get('name'):
                self.set_name(device_id, device_param['name'])

    def get_device(self, device_id=None):
        if self.registered(device_id):
            return self._device.copy().get(device_id)
        return self._device.copy()

    def get_json_string(self, device_id=None, indent=4):
        return json.dumps(self.get_device(device_id), indent=indent)

    def delete_device(self, device_id):
        if not self.registered(device_id):
            return False
        self._device.pop(device_id)
        return True

    def registered(self, device_id):
        return self._device.get(device_id) is not None
