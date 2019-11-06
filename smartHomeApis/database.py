#-*- coding:utf8 -*-
# Copyright (c) 2019 barriery
# Python release: 3.7.0
import pymysql
import json
import sshtunnel
import copy
import datetime

class DatabaseManager(object):
    def __init__(self, remote_ip, remote_usr, remote_pwd, database_usr, database_pwd, database_name):
        self.server = sshtunnel.SSHTunnelForwarder(
                (remote_ip, 22),
                ssh_username=remote_usr,
                ssh_password=remote_pwd,
                remote_bind_address=('localhost', 3306))
        self.server.start()
        self.conn = pymysql.connect(
                user=database_usr,
                password=database_pwd,
                host='127.0.0.1',
                database=database_name,
                port=self.server.local_bind_port)
        self._pre_terminal_infos = None
    def __del__(self):
        self.conn.close()
        self.server.stop()
    def in_table(self, tid, table, cursor, conn):
        sql_cmd = "select * from %s where id='%s'" % (table, tid)
        cursor.execute(sql_cmd)
        data = cursor.fetchone()
        return data is not None
    def insert(self, table, params, cursor, conn):
        keys = None
        values = None
        for k, v in params.items():
            keys = k if keys is None else "%s, %s"%(keys, k)
            values = "'%s'"%v if values is None else "%s, '%s'"%(values, v)
        sql_cmd = "insert into %s (%s) values (%s)" % (table, keys, values)
        cursor.execute(sql_cmd)
        conn.commit()
    def update(self, table, tid, params, cursor, conn):
        values = None
        for k, v in params.items():
            values = "%s='%s'"%(k, v) if values is None else "%s, %s='%s'"%(values, k, v)
        sql_cmd = "update %s set %s where id='%s'" % (table, values, tid)
        cursor.execute(sql_cmd)
        conn.commit()
    def update_if_cannot_insert(self, table, tid, params, cursor, conn):
        if self.in_table(tid, table, cursor, conn):
            # update do not need 'id'
            self.update(table, tid, params, cursor, conn)
        else:
            params['id'] = tid
            self.insert(table, params, cursor, conn)
    def push_device_to_table(self, dev, location, timestamp, cursor, conn):
        did = dev.getter('id')
        table = 'deviceinfo'
        keys = ['inroom', 'localip', 'token', 'type', 'model', 'name']
        params = {k: dev.getter(k) for k in keys}
        # turn 'status' to 'data': {"status":1}
        params['data'] = json.dumps({'status': dev.getter('status')})
        params['location'] = location
        params['timestamp'] = timestamp
        self.update_if_cannot_insert(table, did, params, cursor, conn)
    def push_sensor_to_table(self, ssr, location, timestamp, cursor, conn):
        sid = ssr.getter('id')
        table = 'deviceinfo'
        keys = ['inroom', 'type', 'model', 'name']
        params = {k: ssr.getter(k) for k in keys}
        # 'data' need json.dumps
        params['data'] = json.dumps(ssr.getter('data'))
        params['location'] = location
        params['timestamp'] = timestamp
        self.update_if_cannot_insert(table, sid, params, cursor, conn)
    def is_repeated(self, tid, cur_terminal):
        if self._pre_terminal_infos is None:
            return False
        pre_terminal = self._pre_terminal_infos[tid]
        return pre_terminal == cur_terminal # deep compare
    def push_to_database(self, terminal_infos, repeated_filter=True):
        with self.conn.cursor() as cursor:
            location = terminal_infos.location
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            for tid, ins in terminal_infos.items():
                if repeated_filter and self.is_repeated(tid, ins):
                    continue
                if ins.is_device():
                    self.push_device_to_table(ins, location, timestamp, cursor, self.conn)
                elif ins.is_sensor():
                    self.push_sensor_to_table(ins, location, timestamp, cursor, self.conn)
                else:
                    raise Exception('known terminal')
        self._pre_terminal_infos = {k: v.copy() for k, v in terminal_infos.items()}
