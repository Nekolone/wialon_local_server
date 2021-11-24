import socket
import time

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("127.0.0.1", 12345))


while True:
    data = client.recv(1024)
    print(data.decode("utf-8"))
    time.sleep(0.2)
