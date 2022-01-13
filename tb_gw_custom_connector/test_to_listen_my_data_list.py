from parser import Parser

log = open("../error_srtings", "r")

while log:
    msg = log.readline().replace("\n", "\r\n")
    print(msg)
    print(Parser().parse_v1("-", msg))

