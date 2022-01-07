from service import Thread, time, self_loop, Lock, Wiretapping


class DeviceManager:
    def __init__(self, config, gateway, sleep_time=0.1):
        self._gateway = gateway
        self._config = config
        # self._name = self._config.get("name", "Custom %s connector " + ''.join(
        #     choice(ascii_lowercase) for _ in range(5)))
        self._name = self._gateway.name
        self._type = self._config.get("type", "default")
        self.timeout = self._config.get("timeout", 30)
        self._check_length = self._config.get("check_length", 10)
        self.accepted_list = self._config.get("accepted_list", {"0": "0"})  # Загрузка id разрешенных девайсов и их
        # имен для подключения к TB в формате "id": "name"
        self._send_rate = self._config.get("send_rate", 0.5)
        self.tr_device_proc = Thread(target=self._device_process)
        self._csc_lock = Lock()
        self.device_list = {}
        self.data_storage = {}
        self.converted_data = []
        self.unknown_devices = set()
        self.disconnected_devices = set()
        self._status = False
        self.loop = True
        self.time = None
        self.sleep_time = sleep_time
        self._update_send_time()

    def add_device_to_process(self, device):
        device.set_last_data_time(self._check_length)
        self.device_list[device.id] = device
        self.data_storage[device.id] = []

    @property
    def status(self):
        return self._status

    @self_loop
    def _device_process(self):
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

    def _prepare_data_to_send(self):
        for d in self.device_list:
            if d not in self.accepted_list:
                self.unknown_devices.add(d)
                continue

            for it in self.data_storage[d]:
                if not it:
                    continue

                device_msg = {
                    "deviceName": f"{self.accepted_list[d]}",
                    "deviceType": self._type,
                    "attributes": [
                        {"connected_device_id": d},
                        {"connection_status": "active"},
                        {"time_status": self.device_list[d].time_status()}
                    ],
                    "telemetry": [
                        {"data": it}
                    ]
                }
                self.converted_data.append(device_msg)

        self.converted_data.append({
            "deviceName": self._name,
            "deviceType": self._type,
            "attributes": [
                {"connected_devices_id": [d for d in self.device_list]},
                {"unknown_device_id": [d for d in self.unknown_devices]},
                {"disconnected_devices": [d for d in self.disconnected_devices]}
            ],
            "telemetry": [
                {"0": "0"}
            ]
        })

    def _send_data_to_server(self):
        for msg in self.converted_data:
            self._gateway.send_to_storage(msg["deviceName"], msg)

    def _clear_data(self):
        self.data_storage = {}
        self.converted_data = []
        self.disconnected_devices = set()
        self.unknown_devices = set()

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
                "deviceType": self._type,
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

    def join(self):
        self.tr_device_proc.join()
        self._collect_data_from_devices()
        self._prepare_data_to_send()
        self._send_data_to_server()

    def stop(self):
        self.loop = False
        self._status = False
