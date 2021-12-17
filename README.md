# wialon_local_server

**/usr/local/lib/python3.8/dist-packages/thingsboard_gateway/extensions/serial** 
- custom_serial_connector - кастомный код коннектора

**/etc/thingsboard-gateway/config**
- tb_gateway.yaml - настройки подключения гетвея к ThingsBoard
```
    host: 192.168.35.204
    port: 1883
    ....
    подключать нужный коннектор, в нашем случае 
    Custom Serial Connector
```
- custom_serial.json - настройка подключения девайса к гетвею
```
{
  "name":"Custom serial connector",
  "type": "wialon device",
  "accepted_list":{
    "id":"pass",
    "id":"pass"
  }
}
```

***полезные ссылки***
- https://thingsboard.io/docs/iot-gateway/custom/
- https://thingsboard.io/docs/iot-gateway/install/pip-installation/
- http://192.168.35.204:8080/devices