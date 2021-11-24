from threading import Thread
import time
from service import lock


def self_loop(f):
    def decorator(self):
        while self.loop:
            f(self)
            time.sleep(self.sleep_time)

    return decorator


class Device:
    def __init__(self, user, addr, login_msg):
        self.user = user
        self.addr = addr
        self.login_msg = login_msg
        self.parsed_msg = self.parse(login_msg)
        self.id = 1111
        # self.id = None
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

    def parse(self, msg):
        return msg
        # make some magic stuff


class DeviceManager:
    def __init__(self, send_rate=60, sleep_time=0.1):
        self.tr_device_proc = Thread(target=self._device_process)
        self.device_list = {}
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
        self.data_storage[device.id] = []
        lock.release()
        # добавление

    def _device_listen(self, device):
        print("next?")
        device.status = "connected"
        while device.zero_msg_count < 5 and self.loop:
            msg = device.user.recv(1024)
            print(msg)
            new_info = device.parse(msg)
            """
            добавть поддержку сообщений большей длинны
            """
            if len(new_info) > 0:
                lock.acquire()
                self.data_storage[device.id].append(new_info)
                lock.release()
            if len(new_info) == 0:
                device.add_zmc()
                time.sleep(1)
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
            self.data_storage[d] = []

    def _check_device_status(self):
        for d in self.device_list.copy():
            match self.device_list[d].status:
                case "connected":
                    continue

                case "disconnected":
                    print("here cds2?")
                    self._delete_device(self.device_list[d])

                case "new":
                    print("here cds3?")
                    self._start_listening_device(self.device_list[d])

    def _start_listening_device(self, device):
        print("sld")
        print(device)
        device.thread_link = Thread(target=self._device_listen, args=([device]))
        device.thread_link.start()

    def _delete_device(self, d):
        lock.acquire()
        print(d)
        self.device_list.pop(d.id, None)
        print(self.device_list)
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
        return True

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
