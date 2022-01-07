from service import datetime


class Parser:
    def __init__(self):
        self.crc_table = [
            0x0000, 0xC0C1, 0xC181, 0x0140, 0xC301, 0x03C0, 0x0280, 0xC241,
            0xC601, 0x06C0, 0x0780, 0xC741, 0x0500, 0xC5C1, 0xC481, 0x0440,
            0xCC01, 0x0CC0, 0x0D80, 0xCD41, 0x0F00, 0xCFC1, 0xCE81, 0x0E40,
            0x0A00, 0xCAC1, 0xCB81, 0x0B40, 0xC901, 0x09C0, 0x0880, 0xC841,
            0xD801, 0x18C0, 0x1980, 0xD941, 0x1B00, 0xDBC1, 0xDA81, 0x1A40,
            0x1E00, 0xDEC1, 0xDF81, 0x1F40, 0xDD01, 0x1DC0, 0x1C80, 0xDC41,
            0x1400, 0xD4C1, 0xD581, 0x1540, 0xD701, 0x17C0, 0x1680, 0xD641,
            0xD201, 0x12C0, 0x1380, 0xD341, 0x1100, 0xD1C1, 0xD081, 0x1040,
            0xF001, 0x30C0, 0x3180, 0xF141, 0x3300, 0xF3C1, 0xF281, 0x3240,
            0x3600, 0xF6C1, 0xF781, 0x3740, 0xF501, 0x35C0, 0x3480, 0xF441,
            0x3C00, 0xFCC1, 0xFD81, 0x3D40, 0xFF01, 0x3FC0, 0x3E80, 0xFE41,
            0xFA01, 0x3AC0, 0x3B80, 0xFB41, 0x3900, 0xF9C1, 0xF881, 0x3840,
            0x2800, 0xE8C1, 0xE981, 0x2940, 0xEB01, 0x2BC0, 0x2A80, 0xEA41,
            0xEE01, 0x2EC0, 0x2F80, 0xEF41, 0x2D00, 0xEDC1, 0xEC81, 0x2C40,
            0xE401, 0x24C0, 0x2580, 0xE541, 0x2700, 0xE7C1, 0xE681, 0x2640,
            0x2200, 0xE2C1, 0xE381, 0x2340, 0xE101, 0x21C0, 0x2080, 0xE041,
            0xA001, 0x60C0, 0x6180, 0xA141, 0x6300, 0xA3C1, 0xA281, 0x6240,
            0x6600, 0xA6C1, 0xA781, 0x6740, 0xA501, 0x65C0, 0x6480, 0xA441,
            0x6C00, 0xACC1, 0xAD81, 0x6D40, 0xAF01, 0x6FC0, 0x6E80, 0xAE41,
            0xAA01, 0x6AC0, 0x6B80, 0xAB41, 0x6900, 0xA9C1, 0xA881, 0x6840,
            0x7800, 0xB8C1, 0xB981, 0x7940, 0xBB01, 0x7BC0, 0x7A80, 0xBA41,
            0xBE01, 0x7EC0, 0x7F80, 0xBF41, 0x7D00, 0xBDC1, 0xBC81, 0x7C40,
            0xB401, 0x74C0, 0x7580, 0xB541, 0x7700, 0xB7C1, 0xB681, 0x7640,
            0x7200, 0xB2C1, 0xB381, 0x7340, 0xB101, 0x71C0, 0x7080, 0xB041,
            0x5000, 0x90C1, 0x9181, 0x5140, 0x9301, 0x53C0, 0x5280, 0x9241,
            0x9601, 0x56C0, 0x5780, 0x9741, 0x5500, 0x95C1, 0x9481, 0x5440,
            0x9C01, 0x5CC0, 0x5D80, 0x9D41, 0x5F00, 0x9FC1, 0x9E81, 0x5E40,
            0x5A00, 0x9AC1, 0x9B81, 0x5B40, 0x9901, 0x59C0, 0x5880, 0x9841,
            0x8801, 0x48C0, 0x4980, 0x8941, 0x4B00, 0x8BC1, 0x8A81, 0x4A40,
            0x4E00, 0x8EC1, 0x8F81, 0x4F40, 0x8D01, 0x4DC0, 0x4C80, 0x8C41,
            0x4400, 0x84C1, 0x8581, 0x4540, 0x8701, 0x47C0, 0x4680, 0x8641,
            0x8201, 0x42C0, 0x4380, 0x8341, 0x4100, 0x81C1, 0x8081, 0x4040
        ]

    def parse_login(self, device):
        nothing, msg_type, msg_params = device.login_msg.split("#")

        if msg_type == "L":
            params = msg_params.split(";")
            if len(params) == 4:
                device.protocol_ver, device.id, device.password, device.crc = params
                device.parse = self.parse_v2
                return
            if len(params) == 2:
                device.id, device.password = params
                device.parse = self.parse_v1
                return

            print("login error, disconnect device")
            return

        """
        not a login msg
        """
        return

    def parse_v1(self, device, msg):
        nothing, msg_type, msg_params = msg.split("#")
        msg_info = None
        answ = None

        if msg_type == "D":
            # data
            answ, msg_info = self.parse_d_v1(msg_params)
        elif msg_type == "P":
            # ping
            answ = "#AP#\r\n"
            msg_info = []
        elif msg_type == "SD":
            # short data
            answ, msg_info = self.parse_sd_v1(msg_params)
        elif msg_type == "B":
            # black box
            answ, msg_info = self.parse_b_v1(msg_params)
        elif msg_type == "M":
            # driver msg
            answ, msg_info = self.parse_m_v1(msg_params)
        elif msg_type == "I":
            # img
            answ, msg_info = self.parse_i_v1(device, msg_params)

        """
        поискать инфу про пакет с прошивкой и файлом конфигурации
        """

        return answ, msg_type, msg_info

    def parse_v2(self, device, msg):
        nothing, msg_type, msg_params = msg.split("#")
        msg_info = None
        answ = None

        if msg_type == "D":
            # data
            answ, msg_type = self.parse_d_v2(msg_params)
        elif msg_type == "SD":
            # short data
            answ, msg_type = self.parse_sd_v2(msg_params)
        elif msg_type == "P":
            # ping
            answ = "#AP#\r\n"
            msg_info = []
        elif msg_type == "B":
            # black box
            answ, msg_type = self.parse_b_v2(msg_params)
        elif msg_type == "M":
            # driver msg
            answ, msg_type = self.parse_m_v2(msg_params)
        elif msg_type == "I":
            # img
            pass
        elif msg_type == "IT":
            answ, msg_type = self.parse_it_v2(device, msg_params)
        elif msg_type == "T":
            answ, msg_type = self.parse_t_v2(device, msg_params)

        """
        поискать инфу про пакет с прошивкой и файлом конфигурации
        """

        return answ, msg_type, msg_info

    @staticmethod
    def parse_sd_v1(msg_params):
        # date;time;lat1;lat2;lon1;lon2;speed;course;height;sats
        params = msg_params.split(";")
        if len(params) != 10:
            answ = "#ASD#-1\r\n"
            return answ, []
        if not "NA" in params:
            # success
            answ = "#ASD#1\r\n"
            return answ, params
        if "NA" in params[:2]:
            # date & time
            answ = "#ASD#0\r\n"
            return answ, params
        if "NA" in params[2:6]:
            # cords
            answ = "#ASD#10\r\n"
            return answ, params
        if "NA" in params[6:9]:
            # speed, course, height
            answ = "#ASD#11\r\n"
            return answ, params
        if "NA" in params[9:10]:
            # sats
            answ = "#ASD#12\r\n"
            return answ, params

        raise Exception("SD V1 error")

    def parse_sd_v2(self, msg_params):
        # date;time;lat1;lat2;lon1;lon2;speed;course;height;sats;crc16
        params = msg_params.split(";")
        crc = self.check_crc(params[-1], msg_params.replace(params[-1], "").encode("utf-8"))

        if not crc:
            answ = "#ASD#13\r\n"
            return answ, []
        if len(params) != 11:
            answ = "#ASD#-1\r\n"
            return answ, []
        if not "NA" in params:
            # success
            answ = "#ASD#1\r\n"
            return answ, params
        if "NA" in params[:2]:
            # date & time
            params[0] = datetime.utcnow().strftime("%d%m%y")
            params[1] = datetime.utcnow().strftime("%d%m%y")
            answ = "#ASD#0\r\n"
            return answ, params
        if "NA" in params[2:6]:
            # cords
            answ = "#ASD#10\r\n"
            return answ, params
        if "NA" in params[6:9]:
            # speed, course, height
            answ = "#ASD#11\r\n"
            return answ, params
        if "NA" in params[9:10]:
            # sats
            answ = "#ASD#12\r\n"
            return answ, params

        raise Exception("SD V2 error")

    @staticmethod
    def parse_d_v1(msg_params):
        params = msg_params.split(";")
        # date;time;lat1;lat2;lon1;lon2;speed;course;height;sats;hdop;inputs;outputs;adc;ibutton;params

        if len(params) < 16:
            answ = "#AD#-1\r\n"
            return answ, []
        if "NA" in params[:2]:
            # date & time
            answ = "#AD#0\r\n"
        elif "NA" in params[2:6]:
            # cords
            answ = "#AD#10\r\n"
        elif "NA" in params[6:9]:
            # speed, course, height
            answ = "#AD#11\r\n"
        elif "NA" in params[9:10]:
            # sats
            answ = "#AD#12\r\n"
        elif "NA" in params[15:]:
            # adds
            answ = "#AD#15\r\n"
        else:
            # success
            answ = "#AD#1\r\n"
        # d_params = {"date": params[0],
        #             "time": params[1],
        #             "lat1": params[2],
        #             "lat2": params[3],
        #             "lon1": params[4],
        #             "lon2": params[5],
        #             "speed": params[6],
        #             "course": params[7],
        #             "height": params[8],
        #             "sats": params[9],
        #             "hdop": params[10],
        #             "inputs": params[11],
        #             "outputs": params[12],
        #             "adc": params[13],
        #             "ibutton": params[14],
        #             "params": [i.split(":") for i in [p for p in params[15].split(",")]],
        #             }
        return answ, params

    def parse_d_v2(self, msg_params):
        params = msg_params.split(";")
        crc = self.check_crc(params[-1], msg_params.replace(params[-1], "").encode("utf-8"))
        # date;time;lat1;lat2;lon1;lon2;speed;course;height;sats;hdop;inputs;outputs;adc;ibutton;params;crc16

        if not crc:
            answ = "#AD#16\r\n"
            return answ, []
        if len(params) < 16:
            answ = "#AD#-1\r\n"
            return answ, []
        if not "NA" in params:
            # success
            answ = "#AD#1\r\n"
            return answ, params
        if "NA" in params[:2]:
            # date & time
            params[0] = datetime.utcnow().strftime("%d%m%y")
            params[1] = datetime.utcnow().strftime("%d%m%y")
            answ = "#AD#0\r\n"
            return answ, params
        if "NA" in params[2:6]:
            # cords
            answ = "#AD#10\r\n"
            return answ, params
        if "NA" in params[6:9]:
            # speed, course, height
            answ = "#AD#11\r\n"
            return answ, params
        if "NA" in params[9:11]:
            # sats & hdop
            answ = "#AD#12\r\n"
            return answ, params
        if "NA" in params[11:13]:
            # inputs & outputs
            answ = "#AD#13\r\n"
            return answ, params
        if "NA" in params[13:14]:
            # adc
            answ = "#AD#14\r\n"
            return answ, params
        if "NA" in params[15:]:
            # adds
            answ = "#AD#15\r\n"
            return answ, params

    @staticmethod
    def parse_b_v1(msg_params):
        items = msg_params.split("|")
        res = {"SD": [], "D": []}

        for i in items:
            if "NA" in i:
                continue
            if len(i.split(";")) == 10:
                res["SD"].append(i.split(";"))
                continue
            res["D"].append(i.split(";"))

        answ = f"#AB#{len(items)}\r\n"
        return answ, res

    def parse_b_v2(self, msg_params):
        items = msg_params.split("|")
        crc = self.check_crc(items[-1], msg_params.replace(items[-1], "").encode("utf-8"))
        res = {"SD": [], "D": []}

        if not crc:
            answ = "#AB#\r\n"
            return answ, []
        for i in items[:-1]:
            if "NA" in i:
                continue
            if len(i.split(";")) == 11:
                res["SD"].append(i.split(";"))
                continue
            res["D"].append(i.split(";"))

        answ = f"#AB#{len(items) - 1}\r\n"
        return answ, res

    @staticmethod
    def parse_m_v1(msg_params):
        if len(msg_params) > 0:
            answ = "#AM#1\r\n"
            return answ, msg_params
        answ = "#AM#0\r\n"
        return answ, msg_params

    def parse_m_v2(self, msg_params):
        # msg;crc16
        params = msg_params.split(";")
        crc = self.check_crc(params[-1], msg_params.replace(params[-1], "").encode("utf-8"))

        if not crc:
            answ = "#AM#\r\n"
            return answ, []

        if len(msg_params) > 0:
            answ = "#AM#1\r\n"
            return answ, params
        answ = "#AM#0\r\n"
        return answ, params

    @staticmethod
    def parse_i_v1(device, msg_params):
        # I#sz;ind;count;date;time;name\r\nBIN
        params = msg_params.split(";")
        print(msg_params)
        print(params)
        if len(params) != 6:
            answ = "#AI#0\r\n"
            return answ, []

        """
        НАДО ТЕСТИТЬ!!!
        """

        params.append(device.user.recv(int(params[0])))
        answ = f"#AI#{params[1]};1\r\n"

        return answ, params

    def parse_i_v2(self, msg_params):
        pass

    def parse_it_v2(self, device, msg_params):
        params = msg_params.split(";")
        # Date;Time;DriverID;Code;Count;CRC16
        crc = self.check_crc(params[-1], msg_params.replace(params[-1], "").encode("utf-8"))

        if not crc:
            answ = "#AIT#01\r\n"
            return answ, []
        if "NA" in params[:2]:
            # date & time
            params[0] = datetime.utcnow().strftime("%d%m%y")
            params[1] = datetime.utcnow().strftime("%d%m%y")
        if not "NA" in params:
            # success
            answ = "#AIT#1\r\n"
            device.ddd_count = int(params[-2])
            return answ, params

        answ = "#AIT#0\r\n"
        return answ, params

    def parse_t_v2(self, device, msg_params):
        params = msg_params.split(";")
        # Code;Sz;Ind;CRC16;BIN

        if len(params) != 4:
            answ = f"#AT#{params[2]};0\r\n"
            return answ, []
        params.append(device.user.recv(int(params[1])))
        crc = self.check_crc(params[3], params[4])
        if not crc:
            answ = f"#AT#{params[2]};01\r\n"
            return answ, []
        if device.ddd_count == int(params[2]):
            answ = f"#AT#1\r\n"
            device.ddd_count = 0
            return answ, params

        answ = f"#AT#{params[2]};1\r\n"
        return answ, params

    def check_crc(self, crc, msg):
        print(msg)

        if not msg or msg == b"":
            return False

        print(crc)
        return crc == self.crc16(msg)

    def crc16(self, msg):
        crc = 0x0000
        for b in msg:
            crc = (crc >> 8) ^ self.crc_table[(crc ^ b) & 0xFF]

        print(crc)
        return crc
