import socket
import time
from threading import Thread, Lock

lock = Lock()

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("127.0.0.1", 20332))


