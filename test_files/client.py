import socket
import time

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("10.0.0.2", 11115))
server.listen()
server.settimeout(50)


while True:
    usr, adr = server.accept()
    # usr.settimeout(20)
    msg = usr.recv(1024)
    if not msg:
        break
    print(msg)
    usr.send(b"#AL#1\r\n")
    while True:
        try:
            msg = usr.recv(100000)
            if not msg:
                break
            print(msg)
            usr.send(b"#AD#1\r\n")
        except socket.timeout:
            print("in usr timeout triggered")
        # usr.send("#AL#1\r\n".encode("utf-8"))



