from threading import Thread
import time
from datetime import datetime
from service import lock


def self_loop(f):
    def decorator(self):
        while self.loop:
            f(self)
            time.sleep(self.sleep_time)

    return decorator


class Parser:
    def __init__(self):
        pass

    def parse_login(self, device, msg):
        nothing, msg_type, msg_params = msg.split("#")

        match msg_type:
            case "L":
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

        match msg_type:
            case "D":
                # data
                answ, msg_info = self.parse_d_v1(msg_params)
            case "P":
                # ping
                answ = "#AP#\r\n"
                msg_info = []
            case "SD":
                # short data
                answ, msg_info = self.parse_sd_v1(msg_params)
            case "B":
                # black box
                answ, msg_info = self.parse_b_v1(msg_params)
            case "M":
                # driver msg
                answ, msg_info = self.parse_m_v1(msg_params)
            case "I":
                # img
                # answ = "#AI#0\r\n"
                # msg_info = []
                answ, msg_info = self.parse_i_v1(device, msg_params)

        """
        поискать инфу про пакет с прошивкой и файлом конфигурации
        """

        return answ, msg_type, msg_info

    def parse_v2(self, device, msg):
        nothing, msg_type, msg_params = msg.split("#")
        msg_info = None
        answ = None

        match msg_type:
            case "SD":
                answ, msg_type = self.parse_sd_v2(msg_params)

            case "D":
                answ, msg_type = self.parse_d_v2(msg_params)

            case "B ":
                answ, msg_type = self.parse_b_v2(msg_params)

            case "P":
                answ = "#AP#\r\n"
                msg_info = []

            case "M":
                answ, msg_type = self.parse_m_v2(msg_params)

            case "I":
                answ, msg_type = self.parse_i_v2(msg_params)

            case "IT":
                answ, msg_type = self.parse_it_v2(device, msg_params)

            case "T":
                answ, msg_type = self.parse_t_v2(device, msg_params)

        return answ, msg_type, msg_info

    @staticmethod
    def parse_sd_v1(msg_params):
        # date;time;lat1;lat2;lon1;lon2;speed;course;height;sats
        params = msg_params.split(";")
        if len(params) != 10:
            answ = "#ASD#-1\r\n"
            return answ, []

        if not "NA" in params:
            answ = "#ASD#1\r\n"

            """
            тут добавить обработку строк перед отпракой на сервер
            """
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

    def parse_sd_v2(self, msg_params):
        # date;time;lat1;lat2;lon1;lon2;speed;course;height;sats
        params = msg_params.split(";")
        crc = self.check_crc(params[-1:])

        if not crc:
            answ = "#ASD#13\r\n"
            return answ, []

        if len(params) != 11:
            answ = "#ASD#-1\r\n"
            return answ, []

        if not "NA" in params:
            answ = "#ASD#1\r\n"

            """
            тут добавить обработку строк перед отпракой на сервер
            """
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
        answ = "#AI#1\r\n"
        return answ, params

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
            return answ, params

        if not "NA" in params:
            answ = "#AD#1\r\n"

            """
            тут добавить обработку строк перед отпракой на сервер
            """
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

    def parse_d_v2(self, msg_params):
        params = msg_params.split(";")
        crc = self.check_crc(params[-1:])
        # date;time;lat1;lat2;lon1;lon2;speed;course;height;sats;hdop;inputs;outputs;adc;ibutton;params

        if not crc:
            answ = "#AD#16\r\n"
            return answ, []

        if len(params) < 16:
            answ = "#AD#-1\r\n"
            return answ, []

        if not "NA" in params:
            answ = "#AD#1\r\n"

            """
            тут добавить обработку строк перед отпракой на сервер
            """
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

    def parse_b_v1(self, msg_params):
        items = msg_params.split("|")
        res = {
            "SD": [],
            "D": []
        }
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

        crc = self.check_crc(items[-1:])

        res = {
            "SD": [],
            "D": []
        }

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
        params = msg_params.split(";")
        crc = self.check_crc(params[-1:])

        if not crc:
            answ = "#AM#\r\n"
            return answ, []

        if len(msg_params) > 0:
            answ = "#AM#1\r\n"
            return answ, params
        answ = "#AM#0\r\n"
        return answ, params

    def parse_i_v1(self, device, msg_params):
        # I#sz;ind;count;date;time;name\r\nBIN
        params = msg_params.split(";")
        print(msg_params)
        print(params)
        if len(params) != 6:
            answ = "#AI#0\r\n"
            return answ, []

        params.append(device.user.recv(int(params[0])))

        answ = f"#AI#{int(params[1])};{int(params[2])}\r\n"

        return answ, params

    def parse_i_v2(self, msg_params):
        pass

    def parse_it_v2(self, device, msg_params):
        params = msg_params.split(";")
        # Date;Time;DriverID;Code;Count;CRC16

        crc = self.check_crc(params[-1:])

        if not crc:
            answ = "#AIT#01\r\n"
            return answ, []

        if "NA" in params[:2]:
            # date & time
            params[0] = datetime.utcnow().strftime("%d%m%y")
            params[1] = datetime.utcnow().strftime("%d%m%y")

        if not "NA" in params:
            answ = "#AIT#1\r\n"
            device.ddd_count = int(params[-2])
            return answ, params

        answ = "#AIT#0\r\n"
        return answ, params

    def parse_t_v2(self, device, msg_params):
        params = msg_params.split(";")
        # Code;Sz;Ind;CRC16;BIN

        crc = self.check_crc(params[-1:])

        if not crc:
            answ = "#AT#01\r\n"
            return answ, []

    def check_crc(self, param):
        pass


class Device:
    def __init__(self, user, addr, login_msg):
        self.user = user
        self.addr = addr
        self.login_msg = login_msg
        self.id = None
        self.password = None
        self.protocol_ver = 1
        self.parse = None
        self.crc = None
        Parser().parse_login(device=self, msg=login_msg)
        self._status = "new"
        self.thread_link = None
        self._zero_msg_count = 0
        self.ddd = 0

    @property
    def ddd_count(self):
        return self.ddd

    @ddd_count.setter
    def ddd_count(self, ddd):
        self.ddd = ddd

    def add_zmc(self):
        self._zero_msg_count += 1

    @property
    def zero_msg_count(self):
        return self._zero_msg_count

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, st):
        self._status = st
        # st = connected \ disconnected


class DeviceManager:
    def __init__(self, accepted_list, send_rate=60, sleep_time=0.1):
        self.tr_device_proc = Thread(target=self._device_process)
        self.device_list = {}
        self.accepted_list = accepted_list
        self._status = False
        self.loop = True
        self.data_storage = {}
        self.time = None
        self.send_rate = send_rate
        self.sleep_time = sleep_time
        self._update_send_time()

    def add_device_to_process(self, device):
        lock.acquire()
        self.device_list[device.id] = device
        self.data_storage[device.id] = {
            "D": [],
            "SD": [],
            "B": [],
            "M": [],
            "I": []
        }
        lock.release()
        # добавление

    def _device_listen(self, device):
        device.status = "connected"
        while device.zero_msg_count < 5 and self.loop:
            msg = self.recv_msg(device).decode("utf-8").replace("\r\n", "")
            print(msg)
            if len(msg) == 0:
                device.add_zmc()
                time.sleep(1)
                continue
            print("get new msg >>", msg)
            answ, msg_type, msg_info = device.parse(device, msg)
            self.msg_answer(device, answ)
            self.add_info_to_datastorage(device, msg_type, msg_info)
            time.sleep(0.1)
        device.status = "disconnected"
        device.user.close()

    # есчи пуступило 0 байт данных более 5 раз, запустить закрытие потока.
    # Запускаеься на потоке и просто слушает девайсы, при поступлении информации созраняет ее для дальнейшей отправки

    @staticmethod
    def recv_msg(device):
        msg = b""
        while not b"\r\n" in msg:
            msg += device.user.recv(1)
            if msg == b"":
                return ""
            # print(msg)

        return msg

    @property
    def status(self):
        return self._status

    @self_loop
    def _device_process(self):
        self._check_device_status()
        if self.time < time.time():
            self._prepare_data_to_send()
            self._send_data_to_server()
            self._clear_data()
            self._update_send_time()

    def _clear_data(self):
        for d in self.data_storage:
            self.data_storage[d] = {
                "D": [],
                "SD": [],
                "B": [],
                "M": [],
                "I": []
            }

    def _check_device_status(self):
        for d in self.device_list.copy():
            match self.device_list[d].status:
                case "connected":
                    continue

                case "disconnected":
                    self._delete_device(self.device_list[d])

                case "new":
                    self._start_listening_device(self.device_list[d])

    def _start_listening_device(self, device):
        print(device)
        device.thread_link = Thread(target=self._device_listen, args=([device]))
        device.thread_link.start()

    def _delete_device(self, d):
        lock.acquire()
        self.device_list.pop(d.id, None)
        lock.release()

    def _prepare_data_to_send(self):
        pass

    def _send_data_to_server(self):
        print(self.data_storage)
        pass

    def _update_send_time(self):
        self.time = time.time() + self.send_rate * 60

    #         ВОТ ТУТ ЦИКЛ проверяет наличие новых данных и запускает отправку на сервер

    def auth(self, device):
        if self.accepted_list[device.id] == device.password:
            self.msg_answer(device, "#AL#1\r\n")
            return True
        self.msg_answer(device, "#AL#0\r\n")
        return False

    def msg_answer(self, device, answer):
        device.user.send(f"{answer}".encode("utf-8"))

    def start(self):
        self.tr_device_proc.start()
        self._status = True

    def join(self):
        self.tr_device_proc.join()
        self._prepare_data_to_send()
        self._send_data_to_server()

    def stop(self):
        self.loop = False
        self._status = False

    def add_info_to_datastorage(self, device, msg_type, msg_info):
        if msg_type == "B":
            lock.acquire()
            self.data_storage[device.id]["SD"].append(msg_info["SD"])
            self.data_storage[device.id]["D"].append(msg_info["D"])
            lock.release()
            return

        if msg_type == "P":
            return

        lock.acquire()
        self.data_storage[device.id][msg_type].append(msg_info)
        lock.release()
        return
