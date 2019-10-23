# SmartHomeAPI

基于miio协议（python-miio），Django后端的小米智能家居RESTful HTTP API。

## 目前实现

- 定时监控局域网中的智能设备（只能拿到Device Id和Local Ip）
- 以REST APIs形式访问支持Wi-Fi的米家智能设备（台灯和插座）

## TODO

- device类继承Manager.dict，直接操作太过混乱

- token自动化获取（tnl，搞不定）。

  目前获取token手段：使用Android手机下载米家APP(v5.4.49)，用APP连接设备后，token以明文形式记录在APP的log文件（`/SmartHome/logs/\d{4}-\d{2}-\d{2}\.txt`）中。

- 数据库支持

## 环境要求

- python-miio: https://github.com/rytilahti/python-miio
- Django
- Python3

## 使用

```bash
python manage.py runserver 0.0.0.0:8000
```

## 接口设计

访问`/help`显示如下接口文档：

```
PUT
    - Description:  Add a device. The default status of device is off.
    - Path:
        /<int:device_id>
    - Form:
        @localip    IP address of device in LAN
        @token      Device token, which is allocated when the device connects to MI-HOME app
        @name       Device name which is generally set in MI-HOME app (not necessary)
GET
    - Description:  List devices infomation.
    - Path:
        /                   List all devises infomation
        /<int:device_id>    List device infomation corresponding to the device_id
DELETE
    - Description:  Delete a device by device_id.
    - Path:
        /<int:device_id>
POST
    - Description:  Given instructions, control device(Default switch on and off status).
    - Path:
        /<int:device_id>
    - Form:
        @status     on or off(not necessary)
```



## 注意

1. 由于可以通过`GET`方法直接获取每个注册设备的信息，可能存在严重的安全隐患。
2. 设备的插拔不会改变localip与token，设备的重置会改变token

