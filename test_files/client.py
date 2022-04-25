import socket
import time

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("127.0.0.1", 33343))
server.listen()
server.settimeout(5)


while True:
    usr, adr = server.accept()
    # usr.settimeout(20)
    while True:
        try:
            msg = usr.recv(1024)
            if not msg:
                break
            print(msg)
        except socket.timeout:
            print("in usr timeout triggered")
        # usr.send("#AL#1\r\n".encode("utf-8"))



