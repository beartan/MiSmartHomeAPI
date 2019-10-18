# SmartHomeAPI

基于miio协议（python-miio），Django后端的小米智能家居RESTful HTTP API。

## 目前实现

1. 定时监控局域网中的智能设备（只能拿到Device Id和Local Ip）
2. 以REST APIs形式访问支持Wi-Fi的米家智能设备（台灯和插座）

## 环境要求

1. python-miio: https://github.com/rytilahti/python-miio
2. Django
3. Python3

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
        @localip    IP address of device in LAN
        @status     on or off(not necessary)
```



## 注意

由于可以通过`GET`方法直接获取每个注册设备的信息，可能存在严重的安全隐患。