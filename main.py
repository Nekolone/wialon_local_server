# from service import server, accepted_list
import socket
import sys

from device_handler import *

accepted_list = {}

# lock = Lock()

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("192.168.100.107", 10003))


def main():
    server.listen()
    device_handler = DeviceManager(accepted_list, send_rate=0.2)
    device_handler.start()
    sys.stdout = open('test_log.txt', 'a')
    print("server start")
    sys.stdout.close()
    while device_handler.status:
        user, adr = server.accept()
        sys.stdout = open('test_log.txt', 'a')
        print("connected")
        sys.stdout.close()
        msg = user.recv(1024)
        try:

            msg = msg.decode("utf-8").replace("\r\n", "")
            if not msg:
                continue

            sys.stdout = open('test_log.txt', 'a')
            print(f"new device connection MSG >>> {msg}")
            sys.stdout.close()

            device = Device(user, adr, msg)

            # a = f"id - {device.id}, pas - {device.password}, p_ver - {device.protocol_ver}, crc - {device.crc}, parser - {device.parse}"
            # print(a.encode("utf-8"))

            if not device_handler.auth(device):
                continue

            device_handler.add_device_to_process(device)
        except:
            sys.stdout = open('test_log.txt', 'a')
            print(f"ERROR MSG >>> {msg}")
            sys.stdout.close()
            continue

        # при реконнекте с существующим ID сделать так чтоб user обновлялся, но данные


if __name__ == '__main__':
    main()
