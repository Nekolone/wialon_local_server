import serial
import socket
import time
from threading import Thread, Lock
from random import choice
from datetime import datetime
from string import ascii_lowercase
from thingsboard_gateway.connectors.connector import Connector, log  # Import base class for connector and logger
from thingsboard_gateway.tb_utility.tb_utility import TBUtility

_csc_lock = Lock()


def self_loop(f):
    def decorator(self):
        while self.loop:
            f(self)
            time.sleep(self.sleep_time)

    return decorator
