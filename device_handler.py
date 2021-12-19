from threading import Thread
import time
from datetime import datetime
import sys

from threading import Thread, Lock

lock = Lock()


def self_loop(f):
    def decorator(self):
        while self.loop:
            f(self)
            time.sleep(self.sleep_time)

    return decorator


class Parser:
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
                sys.stdout = open('test_log.txt', 'a')
                print("login error, disconnect device")
                sys.stdout.close()
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
                pass
                # answ, msg_type = self.parse_i_v2(msg_params)

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
        answ = "#AD#1\r\n"

        """
        тут добавить обработку строк перед отпракой на сервер
        """
        return answ, params
        #
        # if len(params) < 16:
        #     answ = "#AD#-1\r\n"
        #     return answ, []
        #
        # if "NA" in params[:2]:
        #     # date & time
        #     answ = "#AD#0\r\n"
        #     return answ, params
        #
        # if not "NA" in params:
        #     answ = "#AD#1\r\n"
        #
        #     """
        #     тут добавить обработку строк перед отпракой на сервер
        #     """
        #     return answ, params
        #
        # if "NA" in params[2:6]:
        #     # cords
        #     answ = "#AD#10\r\n"
        #     return answ, params
        #
        # if "NA" in params[6:9]:
        #     # speed, course, height
        #     answ = "#AD#11\r\n"
        #     return answ, params
        #
        # # if "NA" in params[9:11]:
        # #     # sats & hdop
        # #     answ = "#AD#12\r\n"
        # #     return answ, params
        #
        # if "NA" in params[11:13]:
        #     # inputs & outputs
        #     answ = "#AD#13\r\n"
        #     return answ, params
        #
        # if "NA" in params[13:14]:
        #     # adc
        #     answ = "#AD#14\r\n"
        #     return answ, params
        #
        # if "NA" in params[15:]:
        #     # adds
        #     answ = "#AD#15\r\n"
        #     return answ, params

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

    @staticmethod
    def parse_b_v1(msg_params):
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

        crc = self.check_crc(items[-1], msg_params.replace(items[-1], "").encode("utf-8"))

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

        # print(msg_params)
        # print(params)
        if len(params) != 6:
            answ = "#AI#0\r\n"
            return answ, []

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
        # print(msg)

        if not msg or msg == b"":
            return False

        # print(crc)
        return crc == self.crc16(msg)

    def crc16(self, msg):
        crc = 0x0000
        for b in msg:
            crc = (crc >> 8) ^ self.crc_table[(crc ^ b) & 0xFF]

        # print(crc)
        return crc


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
        sys.stdout = open('test_log.txt', 'a')
        print(f"device connected. Device id > {self.id}")
        sys.stdout.close()

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
        # self.f = open('log.txt', 'w')
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
            msg = self.recv_msg(device)
            # print(msg)
            if len(msg) == 0:
                device.add_zmc()
                time.sleep(1)
                continue
            msg = msg.decode("utf-8").replace("\r\n", "")

            sys.stdout = open('test_log.txt', 'a')

            print("get new msg >>", msg)
            sys.stdout.close()
            answ, msg_type, msg_info = device.parse(device, msg)
            self.msg_answer(device, answ)
            self.add_info_to_datastorage(device, msg_type, msg_info)
            time.sleep(0.1)
        device.status = "disconnected"
        device.user.close()

        sys.stdout = open('test_log.txt', 'a')
        print(f"device disconnected. Device id > {device.id}")
        sys.stdout.close()

    # есчи пуступило 0 байт данных более 5 раз, запустить закрытие потока.
    # Запускаеься на потоке и просто слушает девайсы, при поступлении информации созраняет ее для дальнейшей отправки

    @staticmethod
    def recv_msg(device):
        msg = b""
        while not b"\r\n" in msg:
            msg += device.user.recv(1)
            if msg == b"":
                return b""
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
        time.sleep(0.5)

    def _clear_data(self):
        self.data_storage = {}
        for d in self.device_list:
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
        # print(device)
        device.thread_link = Thread(target=self._device_listen, args=([device]))
        device.thread_link.start()

    def _delete_device(self, d):
        lock.acquire()
        self.device_list.pop(d.id, None)
        lock.release()

    def _prepare_data_to_send(self):
        pass

    def _send_data_to_server(self):
        # print(self.data_storage)
        pass

    def _update_send_time(self):
        self.time = time.time() + self.send_rate * 60

    #         ВОТ ТУТ ЦИКЛ проверяет наличие новых данных и запускает отправку на сервер

    def auth(self, device):
        if not device.id:
            self.msg_answer(device, "#AL#0\r\n")
            return False
        self.msg_answer(device, "#AL#1\r\n")
        return True

        # if self.accepted_list[device.id] == device.password:
        #     self.msg_answer(device, "#AL#1\r\n")
        #     return True
        # self.msg_answer(device, "#AL#0\r\n")
        # return False

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

        if msg_type == "L":
            return

        lock.acquire()
        self.data_storage[device.id][msg_type].append(msg_info)
        lock.release()
        return
