import sys
import time
import json
import copy
import miio
import socket
import binascii
import codecs
from multiprocessing import Process, Manager

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

def monitor_process(devices, interval=10):
    default_timeout = 5
    sleep_time = max(0, interval - default_timeout)
    while True:
        sys.stdout.write(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())+'\n')
        seen_devices = discover(default_timeout)
        for Id in seen_devices:
            dev = seen_devices.get(Id)
            if Id not in devices:
                dev['inroom'] = 1
                dev['status'] = 0
                devices[Id] = dev
            elif devices[Id].get('localip') != dev.get('localip'):
                temp = devices.get(Id)
                temp['localip'] = dev.get('localip')
                devices[Id] = temp
            elif devices[Id].get('inroom') != 1:
                temp = devices.get(Id)
                temp['inroom'] = 1
                devices[Id] = temp
            elif dev.get('token') and dev.get('token') != devices[Id].get('token'):
                temp = devices.get(Id)
                temp['token'] = dev.get('token')
                devices[Id] = temp
        sys.stdout.write(json.dumps(devices.copy(), indent=4)+'\n')
        time.sleep(sleep_time)

class DeviceManager(object):
    _instance = None
    _process = None
    _device = None
    # _device = {
    #     device_id:
    #        {token, localip, name, status, inroom}
    # }
    
    def __new__(self, *args, **kw):
        if not DeviceManager._instance:
            DeviceManager._instance = super(DeviceManager, self).__new__(self, *args, **kw)
            def gen_get_attr_func(attr):
                def get_attr_func(self, device_id):
                    return self._device.get(device_id).get(attr)
                return get_attr_func
            def gen_set_attr_func(attr):
                def set_attr_func(self, device_id, attr_value):
                    device = self._device.get(device_id)
                    if not device:
                        return False
                    device[attr] = attr_value
                    self._device[device_id] = device
                    return True
                return set_attr_func
            attr_list = ['token', 'localip', 'name', 'status', 'inroom', 'type']
            for attr in attr_list:
                setattr(DeviceManager, 'get_%s' % attr, gen_get_attr_func(attr))
                setattr(DeviceManager, 'set_%s' % attr, gen_set_attr_func(attr))
        return DeviceManager._instance
    
    def __init__(self):
        if not self._process:
            self._device = Manager().dict()
            interval = 30
            self._process = Process(target=monitor_process, args=(self._device, interval))
            self._process.daemon = True
            self._process.start()

    #  def add_device(self, device_id, token, localip=None, name=None):
    def add_device(self, device_id, device_param):
        if not self.registered(device_id):
            self._device[device_id] = copy.deepcopy(device_param)
            self.set_status(device_id, 0)
            self.set_inroom(device_id, 0)
            self.set_type(device_id, miio.ceil.Ceil(self.get_localip(device_id), self.get_token(device_id)).info().__str__().split()[0])
        else:
            if device_param.get('token') and device_param.get('token') != self.get_token(device_id):
                self.set_token(device_id, device_param['token'])
                self.set_type(device_id, miio.ceil.Ceil(self.get_localip(device_id), self.get_token(device_id)).info().__str__().split()[0])
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
