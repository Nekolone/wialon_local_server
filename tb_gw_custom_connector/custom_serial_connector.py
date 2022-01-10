import serial
import socket
import time
from threading import Thread, Lock
from random import choice
from datetime import datetime
from string import ascii_lowercase
from thingsboard_gateway.connectors.connector import Connector, log  # Import base class for connector and logger
from thingsboard_gateway.tb_utility.tb_utility import TBUtility

import logging

from device_handler import DeviceManager
from device import Device


class CustomSerialConnector(Thread, Connector):  # Класс кастомного коннектора
    def __init__(self, gateway, config, connector_type):
        super().__init__()  # Initialize parents classes
        self.statistics = {'MessagesReceived': 0, 'MessagesSent': 0}
        self.__config = config  # Загрузка конфигурации из файла конфигурации
        self.__gateway = gateway  # GATEWAY обьект, через него нужно отсылать сообщения
        self.__connector_type = connector_type  # Тип коннектора, нужен для подключения конвертора, но у нас
        # используется кастомный конвертор
        self.setName(self.__config.get("name", "Custom %s connector " % self.get_name() + ''.join(
            choice(ascii_lowercase) for _ in range(5))))  # Получает имя из файла конфигурации для логов

        self._log_level = self.__config.get("logging_level", "DEBUG")
        self._logging_levels = {"DEBUG": logging.DEBUG, "INFO": logging.INFO, "WARNING": logging.WARNING,
                                "ERROR": logging.ERROR, "CRITICAL": logging.CRITICAL}
        self._log_path = self.__config.get("logging_path", "/etc/thingsboard-gateway/config/tb_log.log")
        logging.basicConfig(filename=self._log_path, level=self._logging_levels[self._log_level])
        logging.info("Starting Custom %s connector", self.get_name())  # Send message to logger

        log.info("Starting Custom %s connector", self.get_name())  # Send message to logger
        self.daemon = True  # Set self thread as daemon
        self.stopped = True  # Service variable for check state
        self.connected = False  # Service variable for check connection to device
        logging.info('Custom connector %s initialization success.', self.get_name())  # Message to logger
        log.info('Custom connector %s initialization success.', self.get_name())  # Message to logger
        # log.info("Devices in configuration file found: %s ",
        #          '\n'.join(device for device in self.devices))  # Message to logger

        self._gateway_ip = self.__config.get("gateway_ip", "127.0.0.1")
        self._gateway_port = self.__config.get("gateway_port", 20332)

        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind((self._gateway_ip, self._gateway_port))
            self.server.listen()
            self.device_handler = DeviceManager(config=self.__config, gateway=self.__gateway)
        except:
            logging.error(f"server creation error, ip:port <{self._gateway_ip}:{self._gateway_port}> is binded")


    def __del__(self):
        self._stop_server()

    def open(self):  # Function called by gateway on start
        self.stopped = False
        self.start()
        self.device_handler.start()

    def close(self):
        # Close connect function, usually used if exception handled in gateway main loop or in connector main loop
        self.stopped = True
        self.device_handler.stop()
        self.device_handler.join()

    def get_name(self):  # Function used for logging, sending data and statistic
        return self.name

    def is_connected(self):  # Function for checking connection state
        return self.connected

    def run(self):  # Вызывается после инициализации
        print("custom serial con run run")
        try:
            logging.debug("all successfully started")
            time.sleep(2)
            while self.device_handler.status and not self.stopped:
                self.connected = self.device_handler.status
                logging.info("waiting for new device connection")
                user, address = self.server.accept()
                msg = user.recv(1024)
                try:
                    msg = msg.decode("utf-8").replace("\r\n", "")
                    if not msg:
                        continue

                    device = Device(user, address, msg)

                    if not self.device_handler.auth(device):
                        continue

                    if device.id in self.device_handler.device_list:
                        self.device_handler.device_list[device.id].new_user_address(user, address)
                        user.send(b"#AL#1\r\n")
                        logging.debug(f"device {device.id} <user> field successfully rewrite")
                        continue

                    self.device_handler.add_device_to_process(device)
                    logging.debug("new device successfully added")

                except:
                    logging.warning(f"LOGIN ERROR MSG >>> {msg}")
                    continue
            logging.info("stop waiting for new devices")
            self._stop_server()
        except:
            self._stop_server()

    def _stop_server(self):  # Остановка сервера на сокете
        try:
            self.server.close()
            logging.debug("server closed")
        except:
            logging.debug("server already closed")

    def server_side_rpc_handler(self, content):
        pass

    def on_attributes_update(self, content):  # Function used for processing attribute update requests from ThingsBoard
        pass
