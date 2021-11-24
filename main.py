from device_handler import *
from service import server


def main():
    server.listen()

    device_handler = DeviceManager(0.2)
    device_handler.start()
    while device_handler.status:
        user, adr = server.accept()
        msg = user.recv(1024)
        print(msg)
        """
        возможно сделать что-то с recv, во избежание возможных ошибок.
        """
        if not msg:
            continue

        device = Device(user, adr, msg)

        if not device_handler.auth(device):
            continue

        device_handler.add_device_to_process(device)

        # при реконнекте с существующим ID сделать так чтоб user обновлялся, но данные


if __name__ == '__main__':
    main()
