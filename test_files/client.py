import socket
import time

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("127.0.0.1", 10003))
server.listen()


while True:
    data = server.recv(1024)
    print(data.decode("utf-8"))
    time.sleep(0.2)
