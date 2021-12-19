import socket
import time

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("192.168.100.107", 10003))
server.listen()

print("start")

while True:
    user, adr = server.accept()
    print("connected")
    while True:
        msg = user.recv(1024)
        print(msg)
        time.sleep(1)
