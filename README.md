# SmartHomeAPI

基于PyXiaomiGateway，python-miio，Django后端的小米智能家居RESTful HTTP API。



仅小米设备而言，我们目前买到的设备有如下几种设备：

- chuangmi.plug.m3  创米插座（需要使用[python-miio](https://github.com/rytilahti/python-miio)库）
- yeelink.light.lamp1  Yeelink台灯（python-miio库支持简单操作，复杂操作需要[python-yeelight](https://github.com/skorokithakis/python-yeelight)库）
- lumi.gateway.v3       绿米网关（需要使用[PyXiaomiGateway](https://github.com/Danielhiversen/PyXiaomiGateway)库）
- Aqara温湿度传感器  支持PyXiaomiGateway库控制
- 米家蓝牙温湿度计     不支持米家普通网关控制（需要使用特殊的蓝牙网关，比如米家床头灯，米家1090P智能摄像机，yeelight智能LED吸顶灯等）

智能家居目前没有一个统一的协议，就算是同一家公司的设备也多种多样。随着设备的增加会变得越来越复杂，个人基本无法完成，最好是借助其他较为完善的平台进行改造开发。



> 但我们仅基于有限的设备做几个demo cases，不需要考虑所有设备。



参考home assistant：

- 采用轮询方式更新设备信息。受限于设备单向通信问题（手动变更设备状态，设备不会发送变更信息给主机），采用轮询来更新主机上设备信息。
- 设备token和网关密码等需要用户自己获取（可能有帮助：https://github.com/xcray/miio-by-CSharp）。
  - 获取token手段：使用Android手机下载米家APP(v5.4.49)，用APP连接设备后，token以明文形式记录在APP的log文件（`/SmartHome/logs/\d{4}-\d{2}-\d{2}\.txt`）中。
  - 获取网关密码信息：在米家APP中打开开发者模式获取信息。

## 目前实现

- 定时监控局域网中的智能设备和传感器
- 以REST APIs形式访问支持Wi-Fi的米家智能设备和传感器
- 支持将监控数据上传到远程数据库



## 环境要求

- python-miio: https://github.com/rytilahti/python-miio
- PyXiaomiGateway: https://github.com/barrierye/PyXiaomiGateway
- Django
- Python3

## 使用

1. 安装环境

```bash
sh build.sh
```

2. 修改配置

   ```bash
   mv smartHomeApis/config.example.py smartHomeApis/config.py # modify it
   ```

3. 运行后端

   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

## 接口设计

访问`/help`显示如下接口文档：

```
PUT
    - Description:  Add a device. The default status of device is off.
    - Path:
        /<str:did>
    - Form:
        @localip    IP address of device in LAN
        @token      Device token, which is allocated when the device connects to MI-HOME app
        @name       Device name which is generally set in MI-HOME app (not necessary)
GET
    - Description:  List terminals(include devices and sensors) infomation.
    - Path:
        /           List all terminals infomation
        /<int:tid>  List terminal infomation corresponding to the tid
DELETE
    - Description:  Delete a terminal by tid.
    - Path:
        /<int:tid>
POST
    - Description:  Given instructions, control device(Default switch on and off status).
    - Path:
        /<int:did>
    - Form:
        @status     0 or 1(not necessary)
```



## 注意

1. 由于可以通过`GET`方法直接获取每个注册设备的信息，存在严重的安全隐患。
2. 后端会持续将设备信息发送到数据库，存在严重的隐私安全隐患。
3. 设备的插拔不会改变localip与token，设备的重置会改变token

