import logging


class CustomConverter:
    def __init__(self, conv_type, dev_man):
        self.conv_type = conv_type
        self.dev_man = dev_man

    def convert(self):
        converted_data = []

        for d in self.dev_man.device_list:
            if d not in self.dev_man.accepted_list:
                self.dev_man.unknown_devices.add(d)
                continue

            for it in self.dev_man.data_storage[d]:
                if not it:
                    continue

                device_msg = {
                    "deviceName": f"{self.dev_man.accepted_list[d]}",
                    "deviceType": self.dev_man.gw_type,
                    "attributes": [
                        {"connected_device_id": d},
                        {"connection_status": "active"},
                        {"time_status": self.dev_man.device_list[d].time_status()}
                    ],
                    "telemetry": [
                        {"data": it}
                    ]
                }
                converted_data.append(device_msg)

        converted_data.append({
            "deviceName": self.dev_man.gw_name,
            "deviceType": self.dev_man.gw_type,
            "attributes": [
                {"connected_devices_id": [d for d in self.dev_man.device_list]},
                {"unknown_device_id": [d for d in self.dev_man.unknown_devices]},
                {"disconnected_devices": [d for d in self.dev_man.disconnected_devices]}
            ],
            "telemetry": [
                {"0": "0"}
            ]
        })
        logging.debug("data conversion successfully")
        return converted_data
