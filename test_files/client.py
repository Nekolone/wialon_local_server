import socket
import time

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.connect(("192.168.100.107", 10003))

log = open("test_log1.txt", "r")

while True:
    server.send(log.readline().replace("\n", "\r\n").encode("utf-8"))
    msg = server.recv(1024)
    time.sleep(10)
