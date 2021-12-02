from service import server, accepted_list
from device_handler import *


def main():
    server.listen()

    device_handler = DeviceManager(accepted_list, send_rate=0.2)
    device_handler.start()
    while device_handler.status:
        user, adr = server.accept()
        msg = user.recv(1024).decode("utf-8").replace("\r\n", "")
        # msg = user.recv(1024).decode("utf-8").replace("\r\n", "")
        print(msg)
        """
        возможно сделать что-то с recv, во избежание возможных ошибок.
        """
        if not msg:
            continue

        device = Device(user, adr, msg)

        a = f"id - {device.id}, pas - {device.password}, p_ver - {device.protocol_ver}, crc - {device.crc}, parser - {device.parse}"
        print(a.encode("utf-8"))

        if not device_handler.auth(device):
            continue

        device_handler.add_device_to_process(device)

        # при реконнекте с существующим ID сделать так чтоб user обновлялся, но данные


if __name__ == '__main__':
    main()
