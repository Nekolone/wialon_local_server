import string

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

        self.device_handle = DeviceManager(config=self.__config, gateway=self.__gateway)

        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind((self._gateway_ip, self._gateway_port))
            self.server.listen()
        except:
            logging.error(f"server creation error, ip:port <{self._gateway_ip}:{self._gateway_port}> is binded")

    def __del__(self):
        self._stop_server()

    def open(self):  # Function called by gateway on start
        self.stopped = False
        self.start()
        self.device_handle.start()

    def close(self):
        # Close connect function, usually used if exception handled in gateway main loop or in connector main loop
        self.stopped = True
        self.device_handle.stop()
        self.device_handle.join()

    def get_name(self):  # Function used for logging, sending data and statistic
        return self.name

    def is_connected(self):  # Function for checking connection state
        return self.connected

    def run(self):  # Вызывается после инициализации
        try:
            logging.debug("all successfully started")
            time.sleep(2)
            while not self.stopped:
                self.connected = self.device_handle.status
                logging.info("waiting for new device connection")
                try:
                    user, address = self.server.accept()
                    user.settimeout(30.0)
                    msg = user.recv(1024)
                    try:
                        msg = msg.decode("utf-8").replace("\r\n", "")
                        if not msg:
                            continue

                        device = Device(user, address, msg)

                        if not self.device_handle.auth(device):
                            continue

                        if device.id in self.device_handle.device_list:
                            self.device_handle.device_list[device.id].new_user_address(user, address)
                            logging.debug(f"device {device.id} <user> field successfully rewrite")
                            continue

                        self.device_handle.add_device_to_process(device)
                        logging.debug("device successfully added")

                    except:
                        logging.warning(f"LOGIN ERROR MSG >>> {msg}")
                        continue
                except:
                    logging.error("server error.  working")
            logging.info("stop waiting for new devices")
            self._stop_server()
        except:
            logging.error("run error, close server")
            self._stop_server()

    def _stop_server(self):  # Остановка сервера на сокете
        try:
            self.device_handle.stop()
            # self.device_handle.stop_all_child_threads()
            self.server.close()
            logging.debug("server closed")
        except:
            logging.debug("server already closed")

    def server_side_rpc_handler(self, content):
        pass

    def on_attributes_update(self, content):  # Function used for processing attribute update requests from ThingsBoard
        pass


class DeviceManager:
    def __init__(self, config, gateway):
        self._gateway = gateway
        self._config = config
        # self._name = self._config.get("name", "Custom %s connector " + ''.join(
        #     choice(ascii_lowercase) for _ in range(5)))
        self.gw_name = self._gateway.name
        self.gw_type = self._config.get("type", "default")
        self.timeout = self._config.get("timeout", 5)
        self._check_length = self._config.get("check_length", 10)
        self.accepted_list = self._config.get("accepted_list", {"0": "0"})  # Загрузка id разрешенных девайсов и их
        # имен для подключения к TB в формате "id": "name"
        self._send_rate = self._config.get("send_rate", 0.5)
        self.tr_device_proc = Thread(target=self._device_process)
        self.converter = CustomConverter(conv_type="default", dev_man=self)
        self.device_list = {}
        self.data_storage = {}
        self.converted_data = []
        self.unknown_devices = set()
        self.disconnected_devices = set()

        self.msg_service = CheckService

        self._status: bool = False
        self._loop: bool = True
        self.time = None
        self._update_send_time()
        logging.debug("DeviceManager initialisation successfully")

    @property
    def loop(self) -> bool:
        return self._loop

    @loop.setter
    def loop(self, val: bool):
        self._loop = val
        if not val:
            self.stop_all_child_threads()

    def add_device_to_process(self, device) -> None:
        device.set_last_data_time(self._check_length)
        self.device_list[device.id] = device
        self.data_storage[device.id] = []
        logging.debug("new device added successfully")

    @property
    def status(self) -> bool:
        return self._status

    @status.setter
    def status(self, value: bool):
        self._status = value

    def _device_process(self) -> None:
        while self.loop:
            self._check_device_status()
            if self.time < time.time():
                self._collect_data_from_devices()
                self._prepare_data_to_send()
                self._send_data_to_server()
                self._clear_data()
                self._update_send_time()
            time.sleep(0.5)

    def _collect_data_from_devices(self):
        for device in self.device_list:
            self.data_storage[device] = self.device_list[device].listening_service_link.get_data()
        logging.debug("data collected successfully")

    def _prepare_data_to_send(self):
        self.converted_data = self.converter.convert()
        logging.debug("data converted successfully")

    def _send_data_to_server(self):
        for msg in self.converted_data:
            self._gateway.send_to_storage(msg["deviceName"], msg)
        logging.debug("data sent successfully")

    def _clear_data(self):
        self.data_storage = {}
        self.converted_data = []
        self.disconnected_devices = set()

    def _update_send_time(self):
        self.time = time.time() + self._send_rate * 60

    def _check_device_status(self):
        for device in self.device_list.copy():
            if self.device_list[device].status == "connected":
                continue

            if self.device_list[device].status == "disconnected":
                if device in self.accepted_list:
                    self._set_connection_status(device, "disconnected")
                self.delete_device(self.device_list[device])
                self.disconnected_devices.add(device)
                continue

            if self.device_list[device].status == "new":
                self._start_listening_device(self.device_list[device])
                continue

    def _set_connection_status(self, d, status):
        self._gateway.send_to_storage(
            self.accepted_list[d],
            {
                "deviceName": f"{self.accepted_list[d]}",
                "deviceType": self.gw_type,
                "attributes": [
                    {"connected_device_id": d},
                    {"connection_status": status}
                ],
                "telemetry": [
                    {"0": "0"}
                ]
            }
        )

    def _start_listening_device(self, device):
        # device.listening_service_link = ListeningService(device, self.timeout, self.msg_service.check_msg)
        device.listening_service_link.timeout = self.timeout
        device.listening_service_link.check_msg = self.msg_service.check_msg
        # device.thread_link = Thread(target=device.listening_service_link.listen_device)
        device.thread_link.start()
        logging.debug("new wiretapping thread started successfully")

    def delete_device(self, d):
        self.device_list.pop(d.id, None)

    @staticmethod
    def auth(device):
        if not device.id:
            device.user.send(b"#AL#0\r\n")
            return False
        device.user.send(b"#AL#1\r\n")
        return True
        #
        # if self.accepted_list[device.id] == device.password:
        #     self.msg_answer(device, "#AL#1\r\n")
        #     return True
        # self.msg_answer(device, "#AL#0\r\n")
        # return False

    def start(self):
        self.status = True
        # self._status = True
        self.loop = True
        self.tr_device_proc.start()
        logging.debug("start DeviceManager successfully")

    def join(self):
        self.tr_device_proc.join()
        self._collect_data_from_devices()
        self._prepare_data_to_send()
        self._send_data_to_server()
        logging.debug("join DeviceManager successfully")

    def stop(self):
        self.loop = False
        self.status = False
        logging.debug("stopping DeviceManager")

    def stop_all_child_threads(self):
        for device in self.device_list:
            device.status = "disconnected"


class Device:
    def __init__(self, user, address, login_msg: string):
        self.user = user
        self.address = address
        self.login_msg: string = login_msg
        self.id: string = None
        self.password: string = None
        # self.protocol_ver = 1
        # self.parse = None
        self._parse_login()
        self.listening_service_link: ListeningService = ListeningService(self)
        self.thread_link = Thread(target=self.listening_service_link.listen_device)
        self._status = "new"
        # self._ddd = 0
        self.last_data_time = []
        self.time_status = lambda: "time_correct" if len(set(self.last_data_time)) > 1 else "time_stopped"
        logging.info(f"device connected. Device id > {self.id}")

    def __del__(self):
        self.status = "disconnected"

    @property
    def status(self) -> string:
        return self._status

    @status.setter
    def status(self, value: string):
        self._status = value
        if value == "disconnected":
            try:
                self.listening_service_link.stop()
            except:
                logging.debug("cant stop listening service, coz not exist")

    def _parse_login(self):
        _, msg_type, msg_info = self.login_msg.split("#")
        self.id, self.password = msg_info.split(";")
        # ParsingService().parse_login(device=self)

    def set_last_data_time(self, count):
        for i in range(count):
            self.last_data_time.append(i)

    def new_user_address(self, user, address):
        self.user = user
        self.address = address
        if self.status != "disconnected":
            return
        self.status = "connected"
        self.listening_service_link.loop = True
        self.thread_link.start()

    # @property
    # def ddd_count(self):
    #     return self._ddd
    #
    # @ddd_count.setter
    # def ddd_count(self, ddd):
    #     self._ddd = ddd


class ListeningService:
    def __init__(self, device: Device):
        self.device = device

        self._timeout = None

        self._check_msg = None

        self._loop = True

        self._data_storage = []
        self.lock = Lock()
        self.zero_msg_count = 0

    @property
    def loop(self) -> bool:
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, value):
        self._timeout = value

    @property
    def check_msg(self):
        return self._check_msg

    @check_msg.setter
    def check_msg(self, value):
        self._check_msg = value

    def listen_device(self):
        self.device.status = "connected"
        while self.zero_msg_count < self.timeout and self.loop:
            msg = self._recv_msg()
            logging.debug(f"device > {self.device.id} get new msg")
            # print(msg)
            if len(msg) == 0:
                self.zero_msg_count += 1
                time.sleep(1)
                continue
            try:
                self.zero_msg_count = 0
                msg = msg.decode("utf-8").replace("\r\n", "")
                msg_type, msg_time, check_status = self._check_msg(msg)
                if not check_status == "correct":
                    logging.debug(f"device <{self.device.id}> error msg struct {msg}")
                    continue
                # answer, msg_type, msg_info = self.device.parse(self.device, msg)
                self._update_time(msg_time)
                self._answer_to_msg(f"#{msg_type}#1\r\n")
                self._add_to_data_storage(msg_type, msg)
            except:
                logging.error(f"device <{self.device.id}> LISTEN ERROR MSG {msg}")
        self.device.user.close()
        self.device.status = "disconnected"
        logging.info(f"device disconnected. Device id > {self.device.id}")

    def _recv_msg(self) -> string:
        msg = b""
        while b"\r\n" not in msg:
            try:
                msg += self.device.user.recv(1)
                if msg == b"":
                    return b""
            except socket.timeout:
                logging.debug(f"recv from {self.device.id} timeout")

        return msg

    def _answer_to_msg(self, answer: string) -> None:
        self.device.user.send(answer.encode("utf-8"))

    def _add_to_data_storage(self, msg_type: string, msg: string) -> None:
        if msg_type == "P":
            return
        if msg_type == "L":
            return
        self.lock.acquire()
        self._data_storage.append(msg)
        self.lock.release()

    def stop(self):
        self.loop = False

    def get_data(self) -> []:
        self.lock.acquire()
        data = self._data_storage.copy()
        self._data_storage = []
        self.lock.release()
        return data

    def _update_time(self, last_time: string) -> None:
        self.device.last_data_time.pop(0)
        self.device.last_data_time.append(last_time[1])


class CustomConverter:
    def __init__(self, conv_type: string, dev_man: DeviceManager):
        self.conv_type: string = conv_type
        self.dev_man: DeviceManager = dev_man

    def convert(self) -> list:

        converted_data = self._convert_telemetry()

        converted_data.append({
            "deviceName": self.dev_man.gw_name,
            "deviceType": self.dev_man.gw_type,
            "attributes": [
                {"connected_devices_id": [d for d in self.dev_man.device_list]},
                {"unknown_device_id": [d for d in self.dev_man.unknown_devices]},
                {"disconnected_devices": [d for d in self.dev_man.disconnected_devices]}
            ],
            "telemetry": [
                {"0": "0"}
            ]
        })
        # logging.debug("data conversion successfully")
        return converted_data

    def _convert_telemetry(self) -> list:
        telemetry: list = []
        for device in self.dev_man.device_list:
            if device not in self.dev_man.accepted_list:
                self.dev_man.unknown_devices.add(device)
                continue

            for device_telemetry in self.dev_man.data_storage[device]:
                if not device_telemetry:
                    continue

                device_msg = {
                    "deviceName": f"{self.dev_man.accepted_list[device]}",
                    "deviceType": self.dev_man.gw_type,
                    "attributes": [
                        {"connected_device_id": device},
                        {"connection_status": "active"},
                        {"time_status": self.dev_man.device_list[device].time_status()}
                    ],
                    "telemetry": [
                        {"data": device_telemetry}
                    ]
                }
                telemetry.append(device_msg)

        return telemetry


class CheckService:
    def __init__(self):
        self.kw_dict = {
            "L": 2,
            "SD": 10,
            "D": 16,
            "P": 0,
            "B": 1,
            "M": 1,
            "US": 1,
            "UС": 1,
        }

    def check_msg(self, msg: string) -> (string, string, string):
        _, msg_type, msg_params = msg.split("#", 2)
        if self.kw_dict[msg_type] != len(msg_params.split(";")):
            return msg_type, 0, "msg struct error"
        """
        можно добавить доп проверки
        """
        return msg_type, msg_params[1], "correct"


class ParsingService:
    def __init__(self):
        self.crc_table = [
            0x0000, 0xC0C1, 0xC181, 0x0140, 0xC301, 0x03C0, 0x0280, 0xC241,
            0xC601, 0x06C0, 0x0780, 0xC741, 0x0500, 0xC5C1, 0xC481, 0x0440,
            0xCC01, 0x0CC0, 0x0D80, 0xCD41, 0x0F00, 0xCFC1, 0xCE81, 0x0E40,
            0x0A00, 0xCAC1, 0xCB81, 0x0B40, 0xC901, 0x09C0, 0x0880, 0xC841,
            0xD801, 0x18C0, 0x1980, 0xD941, 0x1B00, 0xDBC1, 0xDA81, 0x1A40,
            0x1E00, 0xDEC1, 0xDF81, 0x1F40, 0xDD01, 0x1DC0, 0x1C80, 0xDC41,
            0x1400, 0xD4C1, 0xD581, 0x1540, 0xD701, 0x17C0, 0x1680, 0xD641,
            0xD201, 0x12C0, 0x1380, 0xD341, 0x1100, 0xD1C1, 0xD081, 0x1040,
            0xF001, 0x30C0, 0x3180, 0xF141, 0x3300, 0xF3C1, 0xF281, 0x3240,
            0x3600, 0xF6C1, 0xF781, 0x3740, 0xF501, 0x35C0, 0x3480, 0xF441,
            0x3C00, 0xFCC1, 0xFD81, 0x3D40, 0xFF01, 0x3FC0, 0x3E80, 0xFE41,
            0xFA01, 0x3AC0, 0x3B80, 0xFB41, 0x3900, 0xF9C1, 0xF881, 0x3840,
            0x2800, 0xE8C1, 0xE981, 0x2940, 0xEB01, 0x2BC0, 0x2A80, 0xEA41,
            0xEE01, 0x2EC0, 0x2F80, 0xEF41, 0x2D00, 0xEDC1, 0xEC81, 0x2C40,
            0xE401, 0x24C0, 0x2580, 0xE541, 0x2700, 0xE7C1, 0xE681, 0x2640,
            0x2200, 0xE2C1, 0xE381, 0x2340, 0xE101, 0x21C0, 0x2080, 0xE041,
            0xA001, 0x60C0, 0x6180, 0xA141, 0x6300, 0xA3C1, 0xA281, 0x6240,
            0x6600, 0xA6C1, 0xA781, 0x6740, 0xA501, 0x65C0, 0x6480, 0xA441,
            0x6C00, 0xACC1, 0xAD81, 0x6D40, 0xAF01, 0x6FC0, 0x6E80, 0xAE41,
            0xAA01, 0x6AC0, 0x6B80, 0xAB41, 0x6900, 0xA9C1, 0xA881, 0x6840,
            0x7800, 0xB8C1, 0xB981, 0x7940, 0xBB01, 0x7BC0, 0x7A80, 0xBA41,
            0xBE01, 0x7EC0, 0x7F80, 0xBF41, 0x7D00, 0xBDC1, 0xBC81, 0x7C40,
            0xB401, 0x74C0, 0x7580, 0xB541, 0x7700, 0xB7C1, 0xB681, 0x7640,
            0x7200, 0xB2C1, 0xB381, 0x7340, 0xB101, 0x71C0, 0x7080, 0xB041,
            0x5000, 0x90C1, 0x9181, 0x5140, 0x9301, 0x53C0, 0x5280, 0x9241,
            0x9601, 0x56C0, 0x5780, 0x9741, 0x5500, 0x95C1, 0x9481, 0x5440,
            0x9C01, 0x5CC0, 0x5D80, 0x9D41, 0x5F00, 0x9FC1, 0x9E81, 0x5E40,
            0x5A00, 0x9AC1, 0x9B81, 0x5B40, 0x9901, 0x59C0, 0x5880, 0x9841,
            0x8801, 0x48C0, 0x4980, 0x8941, 0x4B00, 0x8BC1, 0x8A81, 0x4A40,
            0x4E00, 0x8EC1, 0x8F81, 0x4F40, 0x8D01, 0x4DC0, 0x4C80, 0x8C41,
            0x4400, 0x84C1, 0x8581, 0x4540, 0x8701, 0x47C0, 0x4680, 0x8641,
            0x8201, 0x42C0, 0x4380, 0x8341, 0x4100, 0x81C1, 0x8081, 0x4040
        ]

    def parse_login(self, device):
        nothing, msg_type, msg_params = device.login_msg.split("#")

        if msg_type == "L":
            params = msg_params.split(";")
            if len(params) == 4:
                device.protocol_ver, device.id, device.password, device.crc = params
                device.parse = self.parse_v2
                return
            if len(params) == 2:
                device.id, device.password = params
                device.parse = self.parse_v1
                return

            print("login error, disconnect device")
            return

        """
        not a login msg
        """
        return

    def parse_v1(self, device, msg):
        nothing, msg_type, msg_params = msg.split("#")
        msg_info = None
        answ = None

        if msg_type == "D":
            # data
            answ, msg_info = self.parse_d_v1(msg_params)
        elif msg_type == "P":
            # ping
            answ = "#AP#\r\n"
            msg_info = []
        elif msg_type == "SD":
            # short data
            answ, msg_info = self.parse_sd_v1(msg_params)
        elif msg_type == "B":
            # black box
            answ, msg_info = self.parse_b_v1(msg_params)
        elif msg_type == "M":
            # driver msg
            answ, msg_info = self.parse_m_v1(msg_params)
        elif msg_type == "I":
            # img
            answ, msg_info = self.parse_i_v1(device, msg_params)

        """
        поискать инфу про пакет с прошивкой и файлом конфигурации
        """

        return answ, msg_type, msg_info

    def parse_v2(self, device, msg):
        nothing, msg_type, msg_params = msg.split("#")
        msg_info = None
        answ = None

        if msg_type == "D":
            # data
            answ, msg_type = self.parse_d_v2(msg_params)
        elif msg_type == "SD":
            # short data
            answ, msg_type = self.parse_sd_v2(msg_params)
        elif msg_type == "P":
            # ping
            answ = "#AP#\r\n"
            msg_info = []
        elif msg_type == "B":
            # black box
            answ, msg_type = self.parse_b_v2(msg_params)
        elif msg_type == "M":
            # driver msg
            answ, msg_type = self.parse_m_v2(msg_params)
        elif msg_type == "I":
            # img
            pass
        elif msg_type == "IT":
            answ, msg_type = self.parse_it_v2(device, msg_params)
        elif msg_type == "T":
            answ, msg_type = self.parse_t_v2(device, msg_params)

        """
        поискать инфу про пакет с прошивкой и файлом конфигурации
        """

        return answ, msg_type, msg_info

    @staticmethod
    def parse_sd_v1(msg_params):
        # date;time;lat1;lat2;lon1;lon2;speed;course;height;sats
        params = msg_params.split(";")
        if len(params) != 10:
            answ = "#ASD#-1\r\n"
            return answ, []
        if not "NA" in params:
            # success
            answ = "#ASD#1\r\n"
            return answ, params
        if "NA" in params[:2]:
            # date & time
            answ = "#ASD#0\r\n"
            return answ, params
        if "NA" in params[2:6]:
            # cords
            answ = "#ASD#10\r\n"
            return answ, params
        if "NA" in params[6:9]:
            # speed, course, height
            answ = "#ASD#11\r\n"
            return answ, params
        if "NA" in params[9:10]:
            # sats
            answ = "#ASD#12\r\n"
            return answ, params

        raise Exception("SD V1 error")

    def parse_sd_v2(self, msg_params):
        # date;time;lat1;lat2;lon1;lon2;speed;course;height;sats;crc16
        params = msg_params.split(";")
        crc = self.check_crc(params[-1], msg_params.replace(params[-1], "").encode("utf-8"))

        if not crc:
            answ = "#ASD#13\r\n"
            return answ, []
        if len(params) != 11:
            answ = "#ASD#-1\r\n"
            return answ, []
        if not "NA" in params:
            # success
            answ = "#ASD#1\r\n"
            return answ, params
        if "NA" in params[:2]:
            # date & time
            params[0] = datetime.utcnow().strftime("%d%m%y")
            params[1] = datetime.utcnow().strftime("%d%m%y")
            answ = "#ASD#0\r\n"
            return answ, params
        if "NA" in params[2:6]:
            # cords
            answ = "#ASD#10\r\n"
            return answ, params
        if "NA" in params[6:9]:
            # speed, course, height
            answ = "#ASD#11\r\n"
            return answ, params
        if "NA" in params[9:10]:
            # sats
            answ = "#ASD#12\r\n"
            return answ, params

        raise Exception("SD V2 error")

    @staticmethod
    def parse_d_v1(msg_params):
        params = msg_params.split(";")
        # date;time;lat1;lat2;lon1;lon2;speed;course;height;sats;hdop;inputs;outputs;adc;ibutton;params

        if len(params) < 16:
            answ = "#AD#-1\r\n"
            return answ, []
        if "NA" in params[:2]:
            # date & time
            answ = "#AD#0\r\n"
        elif "NA" in params[2:6]:
            # cords
            answ = "#AD#10\r\n"
        elif "NA" in params[6:9]:
            # speed, course, height
            answ = "#AD#11\r\n"
        elif "NA" in params[9:10]:
            # sats
            answ = "#AD#12\r\n"
        elif "NA" in params[15:]:
            # adds
            answ = "#AD#15\r\n"
        else:
            # success
            answ = "#AD#1\r\n"
        # d_params = {"date": params[0],
        #             "time": params[1],
        #             "lat1": params[2],
        #             "lat2": params[3],
        #             "lon1": params[4],
        #             "lon2": params[5],
        #             "speed": params[6],
        #             "course": params[7],
        #             "height": params[8],
        #             "sats": params[9],
        #             "hdop": params[10],
        #             "inputs": params[11],
        #             "outputs": params[12],
        #             "adc": params[13],
        #             "ibutton": params[14],
        #             "params": [i.split(":") for i in [p for p in params[15].split(",")]],
        #             }
        return answ, params

    def parse_d_v2(self, msg_params):
        params = msg_params.split(";")
        crc = self.check_crc(params[-1], msg_params.replace(params[-1], "").encode("utf-8"))
        # date;time;lat1;lat2;lon1;lon2;speed;course;height;sats;hdop;inputs;outputs;adc;ibutton;params;crc16

        if not crc:
            answ = "#AD#16\r\n"
            return answ, []
        if len(params) < 16:
            answ = "#AD#-1\r\n"
            return answ, []
        if not "NA" in params:
            # success
            answ = "#AD#1\r\n"
            return answ, params
        if "NA" in params[:2]:
            # date & time
            params[0] = datetime.utcnow().strftime("%d%m%y")
            params[1] = datetime.utcnow().strftime("%d%m%y")
            answ = "#AD#0\r\n"
            return answ, params
        if "NA" in params[2:6]:
            # cords
            answ = "#AD#10\r\n"
            return answ, params
        if "NA" in params[6:9]:
            # speed, course, height
            answ = "#AD#11\r\n"
            return answ, params
        if "NA" in params[9:11]:
            # sats & hdop
            answ = "#AD#12\r\n"
            return answ, params
        if "NA" in params[11:13]:
            # inputs & outputs
            answ = "#AD#13\r\n"
            return answ, params
        if "NA" in params[13:14]:
            # adc
            answ = "#AD#14\r\n"
            return answ, params
        if "NA" in params[15:]:
            # adds
            answ = "#AD#15\r\n"
            return answ, params

    @staticmethod
    def parse_b_v1(msg_params):
        items = msg_params.split("|")
        res = {"SD": [], "D": []}

        for i in items:
            if "NA" in i:
                continue
            if len(i.split(";")) == 10:
                res["SD"].append(i.split(";"))
                continue
            res["D"].append(i.split(";"))

        answ = f"#AB#{len(items)}\r\n"
        return answ, res

    def parse_b_v2(self, msg_params):
        items = msg_params.split("|")
        crc = self.check_crc(items[-1], msg_params.replace(items[-1], "").encode("utf-8"))
        res = {"SD": [], "D": []}

        if not crc:
            answ = "#AB#\r\n"
            return answ, []
        for i in items[:-1]:
            if "NA" in i:
                continue
            if len(i.split(";")) == 11:
                res["SD"].append(i.split(";"))
                continue
            res["D"].append(i.split(";"))

        answ = f"#AB#{len(items) - 1}\r\n"
        return answ, res

    @staticmethod
    def parse_m_v1(msg_params):
        if len(msg_params) > 0:
            answ = "#AM#1\r\n"
            return answ, msg_params
        answ = "#AM#0\r\n"
        return answ, msg_params

    def parse_m_v2(self, msg_params):
        # msg;crc16
        params = msg_params.split(";")
        crc = self.check_crc(params[-1], msg_params.replace(params[-1], "").encode("utf-8"))

        if not crc:
            answ = "#AM#\r\n"
            return answ, []

        if len(msg_params) > 0:
            answ = "#AM#1\r\n"
            return answ, params
        answ = "#AM#0\r\n"
        return answ, params

    @staticmethod
    def parse_i_v1(device, msg_params):
        # I#sz;ind;count;date;time;name\r\nBIN
        params = msg_params.split(";")
        print(msg_params)
        print(params)
        if len(params) != 6:
            answ = "#AI#0\r\n"
            return answ, []

        """
        НАДО ТЕСТИТЬ!!!
        """

        params.append(device.user.recv(int(params[0])))
        answ = f"#AI#{params[1]};1\r\n"

        return answ, params

    def parse_i_v2(self, msg_params):
        pass

    def parse_it_v2(self, device, msg_params):
        params = msg_params.split(";")
        # Date;Time;DriverID;Code;Count;CRC16
        crc = self.check_crc(params[-1], msg_params.replace(params[-1], "").encode("utf-8"))

        if not crc:
            answ = "#AIT#01\r\n"
            return answ, []
        if "NA" in params[:2]:
            # date & time
            params[0] = datetime.utcnow().strftime("%d%m%y")
            params[1] = datetime.utcnow().strftime("%d%m%y")
        if not "NA" in params:
            # success
            answ = "#AIT#1\r\n"
            device.ddd_count = int(params[-2])
            return answ, params

        answ = "#AIT#0\r\n"
        return answ, params

    def parse_t_v2(self, device, msg_params):
        params = msg_params.split(";")
        # Code;Sz;Ind;CRC16;BIN

        if len(params) != 4:
            answ = f"#AT#{params[2]};0\r\n"
            return answ, []
        params.append(device.user.recv(int(params[1])))
        crc = self.check_crc(params[3], params[4])
        if not crc:
            answ = f"#AT#{params[2]};01\r\n"
            return answ, []
        if device.ddd_count == int(params[2]):
            answ = f"#AT#1\r\n"
            device.ddd_count = 0
            return answ, params

        answ = f"#AT#{params[2]};1\r\n"
        return answ, params

    def check_crc(self, crc, msg):
        print(msg)

        if not msg or msg == b"":
            return False

        print(crc)
        return crc == self.crc16(msg)

    def crc16(self, msg):
        crc = 0x0000
        for b in msg:
            crc = (crc >> 8) ^ self.crc_table[(crc ^ b) & 0xFF]

        print(crc)
        return crc
