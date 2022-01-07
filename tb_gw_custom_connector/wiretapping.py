from threading import Lock
import time


class Wiretapping:
    def __init__(self, device, dm_link):
        self.device = device
        self.dm_link = dm_link
        self._data_storage = []
        self.lock = Lock()
        self.zero_msg_count = 0

    def listen_device(self):
        self.device.status = "connected"
        while self.zero_msg_count < self.dm_link.timeout and self.dm_link.loop:
            msg = self._recv_msg()
            # print(msg)
            if len(msg) == 0:
                self.zero_msg_count += 1
                time.sleep(1)
                continue
            try:
                self.zero_msg_count = 0
                msg = msg.decode("utf-8").replace("\r\n", "")
                # print("get new msg >>", msg)
                print("1")
                answer, msg_type, msg_info = self.device.parse(self.device, msg)
                print("2")
                print(msg_info[1])
                self.device.last_data_time.pop(0)
                self.device.last_data_time.append(msg_info[1])
                print("3")
                print(f"{answer}")
                self._answer_to_msg(answer)
                print("4")
                self._add_to_data_storage(msg_type, msg)
                print("5")
                time.sleep(0.1)
            except:
                print(f"LISTEN ERROR MSG {msg}")
        self.device.status = "disconnected"
        self.device.user.close()
        print(f"device disconnected. Device id > {self.device.id}")

    def _recv_msg(self):
        msg = b""
        while b"\r\n" not in msg:
            msg += self.device.user.recv(1)
            if msg == b"":
                return b""
        return msg

    def _answer_to_msg(self, answer):
        self.device.user.send(f"{answer}".encode("utf-8"))

    def _add_to_data_storage(self, msg_type, msg):
        if msg_type == "P":
            return
        if msg_type == "L":
            return
        self.lock.acquire()
        self._data_storage.append(msg)
        self.lock.release()

    def get_data(self):
        self.lock.acquire()
        data = self._data_storage.copy()
        self._data_storage = []
        self.lock.release()
        return data
