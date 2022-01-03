import collections
import json

tel_f = open("teltonika.json", "r")
telt_data = json.load(tel_f)

params = {}

for item in telt_data:
    id = item.get("Property ID in AVL packet")
    params[id] = {
        "id": id,
        "param_name": item.get("Property Name"),
        "bytes": item.get("Bytes"),
        "type": item.get("Type"),
        "val_range_min": item.get("Value range"),
        "val_range_max": item.get("Multiplier"),
        "multiplier": item.get("Units"),
        "units": item.get("Description").replace("В°", "*"),
        "description": item.get("HW Support").replace(" \n ", "\n").replace("вЂ“", "-").replace("В°", "*").replace(
            "вЂ™", "'").split("\n"),
        "hw_support": item.get("Parameter Group").split("\n"),
        "parameter_group": item.get("FIELD11")}

#
#
# log = open("test_log_an.txt", "r")
#
# params = {}
# types = {"1": "int", "2": "double", "3": "string"}
#
# while data := log.readline().replace("\n", ""):
#     p_list = [res[:1] for res in [p.split(":") for p in [d for d in data.split(";")[-1].split(",")]]]
#     for d in p_list:
#         print(d)
#         if not d in params:
#             params[d[0]] = {}
#         params[d[0]] = {"param_name": "", "bytes": "", "type": "", "val_range_min": "", "val_range_max": "",
#                      "multiplier": "", "units": "", "description": "", "hw_support": "", "parameter_group": ""}
#
# log.close()
# st_params = str(params).replace(", ", ",\n")
#
# print(st_params)
# int_key, not_int = [], []
# for i in params:
#     try:
#         int_key.append(int(i))
#     except:
#         not_int.append(i)
#
# od_params = {}
# for item in sorted(int_key):
#     od_params[str(item)] = params[str(item)]
#
# for item in sorted(not_int):
#     od_params[item] = params[item]
#
# # od_params = collections.OrderedDict(sorted(params.items()))
# # od_params = dict(sorted(params.items()))
#
#
# print(od_params)

res = open("param_res.json", "w")
res.write(json.dumps(params, indent=4))

res.close()
tel_f.close()

"""
[i.split(":") for i in [p for p in params[15].split(",")]]
"""
