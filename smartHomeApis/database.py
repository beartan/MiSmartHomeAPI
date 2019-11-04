#-*- coding:utf8 -*-
# Copyright (c) 2019 barriery
# Python release: 3.7.0
import pymysql
import json
import sshtunnel

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
    def __del__(self):
        self.conn.close()
        self.server.stop()
    def in_table(self, tid, table, cursor, conn):
        sql_cmd = "select * from %s where id='%s'" % (table, tid)
        cursor.execute(sql_cmd)
        data = cursor.fetchone()
        return data is not None
    def insert(self, table, keys, values, cursor, conn):
        sql_cmd = "insert into %s (%s) values (%s)" % (table, keys, values)
        cursor.execute(sql_cmd)
        conn.commit()
    def update(self, table, tid, values, cursor, conn):
        sql_cmd = "update %s set %s where id='%s'" % (table, values, tid)
        cursor.execute(sql_cmd)
        conn.commit()
    def push_to_deviceinfo_table(self, cursor, conn, dev):
        did = dev.getter('id')
        table = 'deviceinfo'
        if self.in_table(did, table, cursor, conn):
            keys = ['inroom', 'localip', 'token', 'type', 'model', 'name', 'status']
            values = ""
            for k in keys[:-1]:
                values += k + "='" + dev.getter(k) + "', "
            values += "status='" + dev.getter('status') + "' "
            self.update(table, did, values, cursor, conn)
        else:
            keys = ['id', 'inroom', 'localip', 'token', 'type', 'model', 'name', 'status']
            values = "'"
            for k in keys[:-1]:
                values += dev.getter(k) + "', '"
            values += dev.getter('status') + "'"
            self.insert(table, ', '.join(keys), values, cursor, conn)
    def push_to_sensorinfo_table(self, cursor, conn, ssr):
        sid = ssr.getter('id')
        table = 'sensorinfo'
        if self.in_table(sid, table, cursor, conn):
            keys = ['inroom', 'type', 'model', 'name', 'data']
            values = ""
            for k in keys[:-1]:
                values += k + "='" + ssr.getter(k) + "', "
            values += "data='" + json.dumps(ssr.getter('data')) + "' "
            self.update(table, sid, values, cursor, conn)
        else:
            keys = ['id', 'inroom', 'type', 'model', 'name', 'data']
            values = "'"
            for k in keys[:-1]:
                values += ssr.getter(k) + "', '"
            values += json.dumps(ssr.getter('data')) + "'"
            self.insert(table, ', '.join(keys), values, cursor, conn)
    def push_to_database(self, terminal_infos):
        with self.conn.cursor() as cursor:
            for tid, ins in terminal_infos.items():
                if ins.is_device():
                    self.push_to_deviceinfo_table(cursor, self.conn, ins)
                elif ins.is_sensor():
                    self.push_to_sensorinfo_table(cursor, self.conn, ins)
                else:
                    raise Exception('known terminal')
