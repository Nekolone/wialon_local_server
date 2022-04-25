import socket
import time

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.connect(("127.0.0.1", 33343))


while True:
    print("123")
    server.send("hehehe".encode("utf-8"))
    server.send("hehehe".encode("utf-8"))
    server.send("hehehe\r\n".encode("utf-8"))
    server.send("hehehe\r\n".encode("utf-8"))

