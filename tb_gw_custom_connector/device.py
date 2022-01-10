import logging

from parser import Parser


class Device:
    def __init__(self, user, address, login_msg):
        self.user = user
        self.address = address
        self.login_msg = login_msg
        self.id = None
        self.password = None
        self.protocol_ver = 1
        self.parse = None
        self._parse_login()
        self.wiretapping = None
        self.thread_link = None
        self._status = "new"
        self._ddd = 0
        self.last_data_time = []
        self.time_status = lambda: "time_correct" if len(set(self.last_data_time)) > 1 else "time_stopped"
        logging.info(f"device connected. Device id > {self.id}")

    def _parse_login(self):
        Parser().parse_login(device=self)

    def set_last_data_time(self, count):
        for i in range(count):
            self.last_data_time.append(i)

    def new_user_address(self, user, address):
        self.user = user
        self.address = address

    @property
    def ddd_count(self):
        return self._ddd

    @ddd_count.setter
    def ddd_count(self, ddd):
        self._ddd = ddd

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, st):
        self._status = st
        # st = connected \ disconnected
