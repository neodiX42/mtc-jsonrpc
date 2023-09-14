import requests
import json
import os
import jsonpickle
from sys import path
from sys import platform

srcDir = "/usr/local/src/" if platform == "darwin" else "/usr/src/"

path.append(srcDir + "mytonctrl/")
from mytoncore import Block, Trans, Message

url = "https://127.0.0.1:54358/"
token = None

def Get(method, params=None):
	global token
	payload = {"method": method, "params": params, "jsonrpc": "2.0", "id": 0}
	payload = json.loads(jsonpickle.encode(payload))
	#print(f"payload: {type(payload)}, {payload}")
	headers = None
	if token is not None:
		headers = {"Authorization": "token " + token}
	response = requests.post(url, json=payload, headers=headers, verify=False) # verify='/path/to/public_key.pem'
	#print(f"response: {type(response.text)}, {response.text}")
	#data = response.json()
	data = jsonpickle.decode(response.text)
	result = data.get("result")
	error = data.get("error")
	if error:
		print(f"error: {error}")
		text = error.get("data").get("message")
		raise Exception(text)
	return result
#end define



###
### Старт программы
###


buff = Get("login", [None, "123"])
token = buff.get("token")
print("token", json.dumps(token, indent=4))

data = Get("status")
print("status",json.dumps(data, indent=4))

data = Get("seqno", ["validator_wallet_001"])
print("seqno", json.dumps(data, indent=4))

# data = Get("nw", ["wallet_001"])
# print("nw", json.dumps(data, indent=4))

# data = Get("mg", ["validator_wallet_001", data.get("addr_init"), 1])
# print("mg", json.dumps(data, indent=4))

# data = Get("aw", ["wallet_001"])
# print("aw", json.dumps(data, indent=4))

data = Get("wl")
print("wl", json.dumps(data, indent=4))

# data = Get("dw", ["wallet_001"])
# print(json.dumps(data, indent=4))

data = Get("vas", ["kf8sQcwWuhwBFrnOTyFPRPTlxrDdlV7rX7DAOTUSyAU9FVx5"])
print("vas", json.dumps(data, indent=4))

data = Get("vah", ["kf8sQcwWuhwBFrnOTyFPRPTlxrDdlV7rX7DAOTUSyAU9FVx5", 100])
print("vah", data)

data = Get("ol")
print("ol", json.dumps(data, indent=4))

# data = Get("vo", [1165461231687465153745135435438151384354343])
# print("vo", json.dumps(data, indent=4))

data = Get("el")
print("el", json.dumps(data, indent=4))

#data = Get("ve")
#print("ve", json.dumps(data, indent=4))

data = Get("vl")
print("vl", json.dumps(data, indent=4))

data = Get("cl")
print("cl", data)

# data = Get("vc", [12345678, 1321346545498416587651687435438748645348])
# print("vc", json.dumps(data, indent=4))

block = Get("GetLastBlock")
print("GetLastBlock:", block)

shards = Get("GetShards", [block])
print("GetShards:", shards)

trans = Get("GetTransactions", [block])
print("GetTransactions:", trans)

messages = Get("GetTrans", [trans[0]])
print("GetTrans:", messages)

data = Get("CheckUpdates")
print("CheckUpdates", json.dumps(data, indent=4))
















