from threading import Thread
import time
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

    def parse_v1(self, msg):
        nothing, msg_type, msg_params = msg.split("#")
        msg_info = None
        answ = None

        match msg_type:
            case "D":
                # data
                answ, msg_info = self.parse_d_v1(msg_params)
            case "P":
                answ = "#AP#\r\n"
                msg_info = []
                """
                пинг записывать на сервер не нужно!!
                """
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
                answ, msg_info = self.parse_i_v1(msg_params)

        """
        поискать инфу про пакет с прошивкой и файлом конфигурации
        """

        return answ, msg_type, msg_info

    def parse_v2(self, msg):
        return msg

    @staticmethod
    def parse_sd_v1(msg_params):
        params = msg_params.split(";")
        # date;time;lat1;lat2;lon1;lon2;speed;course;height;sats
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

    @staticmethod
    def parse_d_v1(msg_params):
        params = msg_params.split(";")
        # date;time;lat1;lat2;lon1;lon2;speed;course;height;sats;hdop;inputs;outputs;adc;ibutton;params
        if len(params) != 16:
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

        if "NA" in params[15:16]:
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
            if len(i.split(";")) == 10:
                an, msg_info = self.parse_sd_v1(i)
                res["SD"].append(msg_info)
                continue
            an, msg_info = self.parse_d_v1(i)
            res["D"].append(msg_info)
        answ = f"#AB#{len(items)}\r\n"
        return answ, res

    @staticmethod
    def parse_m_v1(msg_params):
        if len(msg_params) > 0:
            answ = "#AM#1\r\n"
            return answ, msg_params
        answ = "#AM#0\r\n"
        return answ, msg_params

    def parse_i_v1(self, msg_params):
        # I#sz;ind;count;date;time;name\r\nBIN
        params = msg_params.replace(" ", ";").split(";")
        if len(params) != 7:
            answ = "#AI#0\r\n"
            return answ, []

        """РАБОТА С КАРТИНКАМИ, проверка на размер"""

        answ = "#AI#1\r\n"
        return answ, params



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
            msg = device.user.recv(1024).decode("utf-8").replace("\r\n", " ")
            """разобраться с приемом картинок"""
            if len(msg) == 0:
                device.add_zmc()
                time.sleep(1)
                continue
            print("get new msg >>", msg)
            answ, msg_type, msg_info = device.parse(msg)

            self.msg_answer(device, answ)
            self.add_info_to_datastorage(device, msg_type, msg_info)
            time.sleep(0.1)
        device.status = "disconnected"

    # есчи пуступило 0 байт данных более 5 раз, запустить закрытие потока.
    # Запускаеься на потоке и просто слушает девайсы, при поступлении информации созраняет ее для дальнейшей отправки

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
        lock.acquire()
        print(msg_type)
        self.data_storage[device.id][msg_type].append(msg_info)
        lock.release()

#
# def main():
#     server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     server.bind(("127.0.0.1", 20332))
#     server.listen()
#
#     # event_handler = Eventloop()
#     prev_user = 0
#
#     while True:
#         print("test--")
#         new_device_to_thread(server)
#
#         time.sleep(0.2)
#
#
# def new_device_to_thread(server):
#     user, adr = server.accept()
#     d1 = Thread(target=device_listening, args=([Device(user, adr)]))
#     d1.start()
#     print("new device connected, start new thread")
#
#
# def device_listening(device):
#     while True:
#         new_device_print(device.user, device.addr)
#
#
# def new_device_print(user, adr):
#     print("test info from device")
#     print(user.recv(1024).decode("utf-8"))
#
#
# if __name__ == '__main__':
#     main()
