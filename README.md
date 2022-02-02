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

    host: 192.168.100.104
    port: 1883
    security:
      accessToken: your_token
    ....
    подключать нужный коннектор, в нашем случае 
    Custom Serial Connector
```
- custom_serial.json - конфиг коннектора
```
скопировать файл custom_serial.py в папку config

{
  "name": "Custom serial connector",
  "type": "wialon device",
  "gateway_ip": "192.168.100.107",
  "gateway_port": 10003,
  "timeout": 30,
  "check_length": 15,
  "send_rate": 0.5,
  "logging_level": "DEBUG",
  "logging_path": "/etc/thingsboard-gateway/config/tb_log.log",
  "accepted_list": {
    "1": "test_device",
    "359633107878535": "device1",
    "359633109072822": "device2",
    "359633107886660": "device3",
    "359633107889029": "device4"
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

- tb_log.log
```
файл логов для TB
```

***полезные ссылки***
- https://thingsboard.io/docs/iot-gateway/custom/
- https://thingsboard.io/docs/iot-gateway/install/pip-installation/
- http://192.168.100.104:8080/devices