# wialon_local_server

**/usr/local/lib/python3.8/dist-packages/thingsboard_gateway/extensions/serial** 
- custom_serial_connector - кастомный код коннектора
```
скопировать файл custom_serial_connector.py в папку serial
```

**/etc/thingsboard-gateway/config**
- tb_gateway.yaml - настройки подключения гетвея к ThingsBoard
```
скопировать файл tb_gateway.py в папку config

    host: 192.168.35.204
    port: 1883
    security:
      accessToken: custom_device
    ....
    подключать нужный коннектор, в нашем случае 
    Custom Serial Connector
```
- custom_serial.json - конфиг коннектора
```
скопировать файл custom_serial.py в папку config

{
  "name":"Custom serial connector",
  "type": "wialon device",
  "accepted_list":{
    "id":"device name",
    "id":"device name"
  }
}
```
- connected_devices.json - список девайсов
```
скопировать файл connected_devices.py в папку config

{
  "Custom Serial Connector": "Custom Serial Connector",
  "device1": "Custom Serial Connector",
  "device2": "Custom Serial Connector",
  "device_name": "Custom Serial Connector"
}
```

***полезные ссылки***
- https://thingsboard.io/docs/iot-gateway/custom/
- https://thingsboard.io/docs/iot-gateway/install/pip-installation/
- http://192.168.35.204:8080/devices