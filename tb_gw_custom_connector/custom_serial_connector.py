from service import *


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
        log.info("Starting Custom %s connector", self.get_name())  # Send message to logger
        self.daemon = True  # Set self thread as daemon
        self.stopped = True  # Service variable for check state
        self.connected = False  # Service variable for check connection to device
        # self.devices = {}    # Dictionary with devices, will contain devices configurations, converters for devices and serial port objects
        # self.load_converters()    # Call function to load converters and save it into devices dictionary
        # self.__connect_to_devices()    # Call function for connect to devices
        log.info('Custom connector %s initialization success.', self.get_name())  # Message to logger
        # log.info("Devices in configuration file found: %s ",
        #          '\n'.join(device for device in self.devices))  # Message to logger

        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind(("192.168.100.107", 10003))
            self.server.listen()
            self.device_handler = DeviceManager(config=self.__config, gateway=self.__gateway)
        except:
            print("server creation error")

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

    def get_name(self):  # Function used for logging, sending data and statistic
        return self.name

    def is_connected(self):  # Function for checking connection state
        return self.connected

    def run(self):  # Вызывается после инициализации
        try:
            time.sleep(2)
            while self.device_handler.status and not self.stopped:
                self.connected = self.device_handler.status
                print("start")
                user, adr = self.server.accept()
                msg = user.recv(1024)
                try:
                    msg = msg.decode("utf-8").replace("\r\n", "")
                    if not msg:
                        continue

                    device = Device(user, adr, msg)

                    if not self.device_handler.auth(device):
                        continue

                    if device.id in self.device_handler.device_list:
                        print("this id is already in use")
                        user.send(b"#AL#0\r\n")
                        # user.close()
                        continue

                    self.device_handler.add_device_to_process(device)

                except:
                    print(f"LOGIN ERROR MSG >>> {msg}")
                    continue
            print("stop")
            self._stop_server()
        except:
            self._stop_server()

    def _stop_server(self):
        try:
            print("server closed")
            self.server.close()
        except:
            print("server already closed")

    def server_side_rpc_handler(self, content):
        pass

    def on_attributes_update(self, content):  # Function used for processing attribute update requests from ThingsBoard
        pass
