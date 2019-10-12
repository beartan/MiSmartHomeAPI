# SmartHomeAPI

基于miio协议（python-miio），Django后端的小米智能家居RESTful HTTP API。

## 环境要求

1. python-miio: https://github.com/rytilahti/python-miio
2. Django
3. Python3

## 使用

```bash
python manage.py runserver 0.0.0.0:8000
```

## 注意

由于可以通过`GET`方法直接获取每个注册设备的信息，可能存在严重的安全隐患。