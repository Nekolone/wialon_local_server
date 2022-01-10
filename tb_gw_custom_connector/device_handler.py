from threading import Thread, Lock
import time
import logging

from wiretapping import Wiretapping
from custom_converter import CustomConverter


class DeviceManager:
    def __init__(self, config, gateway):
        self._gateway = gateway
        self._config = config
        # self._name = self._config.get("name", "Custom %s connector " + ''.join(
        #     choice(ascii_lowercase) for _ in range(5)))
        self.gw_name = self._gateway.name
        self.gw_type = self._config.get("type", "default")
        self.timeout = self._config.get("timeout", 30)
        self._check_length = self._config.get("check_length", 10)
        self.accepted_list = self._config.get("accepted_list", {"0": "0"})  # Загрузка id разрешенных девайсов и их
        # имен для подключения к TB в формате "id": "name"
        self._send_rate = self._config.get("send_rate", 0.5)
        self.tr_device_proc = Thread(target=self._device_process)
        self.converter = CustomConverter(conv_type="default", dev_man=self)
        self.device_list = {}
        self.data_storage = {}
        self.converted_data = []
        self.unknown_device = set()
        self.disconnected_devices = set()
        self._status = False
        self.loop = True
        self.time = None
        self._update_send_time()
        logging.debug("DeviceManager initialisation successfully")

    def add_device_to_process(self, device):
        device.set_last_data_time(self._check_length)
        self.device_list[device.id] = device
        self.data_storage[device.id] = []
        logging.debug("new device added successfully")

    @property
    def status(self):
        return self._status

    def _device_process(self):
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
        for d in self.device_list:
            self.data_storage[d] = self.device_list[d].get_data()
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
        for d in self.device_list.copy():
            if self.device_list[d].status == "connected":
                continue

            if self.device_list[d].status == "disconnected":
                if d in self.accepted_list:
                    self.set_connection_status(d, "disconnected")
                self._delete_device(self.device_list[d])
                self.disconnected_devices.add(d)
                continue

            if self.device_list[d].status == "new":
                self._start_listening_device(self.device_list[d])
                continue

    def set_connection_status(self, d, status):
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
        device.wiretapping = Wiretapping(device, self)
        device.thread_link = Thread(target=device.wiretapping.listen_device(), args=())
        device.thread_link.start()
        logging.debug("new wiretapping thread started successfully")

    def _delete_device(self, d):
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
        self._status = True
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
        self._status = False
        logging.debug("stopping DeviceManager")
