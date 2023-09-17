#!/usr/bin/env python3
# -*- coding: utf_8 -*-l

# pip3 install Werkzeug json-rpc
import random
import secrets
import getpass
import psutil
import json
import jsonpickle
import cloudscraper
import pyotp
from sys import path
from werkzeug.wrappers import Request, Response
from werkzeug.datastructures import Headers
from werkzeug.serving import run_simple, make_ssl_devcert
from werkzeug.security import check_password_hash, generate_password_hash
from jsonrpc import JSONRPCResponseManager, dispatcher
from jsonrpc.jsonrpc import JSONRPCRequest
from jsonrpc.exceptions import JSONRPCDispatchException
from sys import platform
import signal

srcDir = "/usr/local/src/" if platform == "darwin" else "/usr/src/"

path.append(srcDir + "mytonctrl/")
from mytoncore import *

local = MyPyClass(__file__)
ton = MyTonCore()

def timeout(signum, frame):
	print('Timeout!')
	exit()

class IP:
	def __init__(self, addr):
		self.addr = addr
		self.wrongNumber = 0
		self.isBlock = False
		self.token = None
		self.inputToken = None
		self.timestamp = None
		self.lifetime = 2629743 # 1 month
		self.allowedIP = None
		self.SetAllowedIP()
	#end define

	def WrongAccess(self):
		raise JSONRPCDispatchException(403, "Forbidden")
	#end define

	def GenerateToken(self):
		self.wrongNumber = 0
		self.token = secrets.token_urlsafe(32)
		self.timestamp = self.TS()
	#end define

	def DestroyToken(self):
		self.wrongNumber = 0
		self.token = None
		self.timestamp = None
	#end define

	def CheckAccess(self):
		if self.isBlock or self.token is None or self.timestamp is None:
			self.WrongAccess()
		timestamp = self.TS()
		isAlive = self.timestamp + self.lifetime > timestamp
		isCorrectToken = self.token == self.inputToken
		if isAlive and isCorrectToken:
			pass
		else:
			self.WrongAccess()
	#end define

	def CheckPassword(self, passwd):
	#	if self.isBlock:
		#	self.WrongAccess()
		passwdHash = ton.GetSettings("passwdHash")

		if passwdHash and check_password_hash(passwdHash, passwd):
			self.GenerateToken()
		else:
			raise JSONRPCDispatchException(403, "Wrong login or password")
	#end define

	def TS(self):
		timestamp = int(time.time())
		return timestamp
	#end define

	def SetAllowedIP(self):
		scraper = cloudscraper.create_scraper()
		r = scraper.get("https://tonadmin.org/ip.json").text
		data_json = json.loads(r)
		self.allowedIP = data_json[0]
	#end define

	def GetAllowedIP(self):
		return self.allowedIP
	#end define
#end class


@Request.application
def application(request):
	global ip
	token = GetUserToken(request)
	ip = GetIp(request.remote_addr, token)

	# rpc = JSONRPCResponseManager.handle(request.data, dispatcher)
	request_str = request.data.decode("utf-8")
	data = jsonpickle.decode(request_str)
	request = JSONRPCRequest.from_data(data)
	rpc = JSONRPCResponseManager.handle_request(request, dispatcher)

	# data = rpc.json
	data = jsonpickle.encode(rpc.data)

	headers = Headers()
	headers.add("Access-Control-Allow-Origin", 'https://tonadmin.org')
	headers.add("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
	headers.add("Access-Control-Allow-Headers", "Content-Length,Content-Type,x-compress,Cache-Control,Authorization")
	response = Response(data, mimetype="application/json", headers=headers)
	return response
#end define

def GetUserToken(request):
	token = None
	buffer = request.headers.get("Authorization")
	if buffer is not None and "token " in buffer:
		buffer = buffer.split(' ')
		token = buffer[1]
	return token
#end define

@dispatcher.add_method
def login(api, passwd, code = None):
	global ip
	ip.CheckPassword(passwd)
	if ton.GetSettings("jsonrpcOTP"):
		OTPSecret = ton.GetSettings("jsonrpcOTPSecret")
		totp = pyotp.TOTP(OTPSecret)
		if totp.now() != code:
			print('exception')
			raise JSONRPCDispatchException(403, "Wrong 2fa code")
	return {"api": api, "token": ip.token}
#end define

@dispatcher.add_method
def logout():
	global ip
	ip.DestroyToken()
	return 1;
#end define


def GetIp(addr, token):
	ipList = GetIpList()
	ip = ipList.get(addr)
	if ip is None:
		ip = IP(addr)
		ipList[addr] = ip
	ip.inputToken = token
	return ip
#end define

def GetIpList():
	ipList = local.buffer.get("ipList")
	if ipList is None:
		ipList = dict()
		local.buffer["ipList"] = ipList
	return ipList
#end define

#end define

@dispatcher.add_method
def status():
	global ip
	ip.CheckAccess()
	config15 = ton.GetConfig15()
	config17 = ton.GetConfig17()
	config34 = ton.GetConfig34()
	config36 = ton.GetConfig36()
	tpsAvg = ton.GetTpsAvg()
	loadavg = GetLoadAvg()
	netLoadAvg = ton.GetNetLoadAvg()
	adnlAddr = ton.GetAdnlAddr()
	mytoncoreStatus = GetServiceStatus("mytoncore")
	rootWorkchainEnabledTime_int = ton.GetRootWorkchainEnabledTime()
	validatorsElectedFor = config15["validatorsElectedFor"]
	electionsStartBefore = config15["electionsStartBefore"]
	electionsEndBefore = config15["electionsEndBefore"]
	stakeHeldFor = config15["stakeHeldFor"]
	minStake = config17["minStake"]
	maxStake = config17["maxStake"]
	totalValidators = config34["totalValidators"]
	onlineValidators = ton.GetOnlineValidators()
	if onlineValidators:
		onlineValidators = len(onlineValidators)
	oldStartWorkTime = config36.get("startWorkTime")
	if oldStartWorkTime is None:
		oldStartWorkTime = config34.get("startWorkTime")
	shardsNumber = ton.GetShardsNumber()
	validatorStatus = ton.GetValidatorStatus()
	fullConfigAddr = ton.GetFullConfigAddr()
	fullElectorAddr = ton.GetFullElectorAddr()
	startWorkTime = ton.GetActiveElectionId(fullElectorAddr)
	validatorIndex = ton.GetValidatorIndex()
	validatorEfficiency = ton.GetValidatorEfficiency()
	validatorWallet = ton.GetValidatorWallet()

	offersNumber = ton.GetOffersNumber()
	complaintsNumber = ton.GetComplaintsNumber()
	if validatorWallet is not None:
		validatorAccount = ton.GetAccount(validatorWallet.addrB64)
	else:
		validatorAccount = None
	#end if

	if startWorkTime == 0:
		startWorkTime = oldStartWorkTime
	#end if

	# Calculate time
	startValidation = startWorkTime
	endValidation = startWorkTime + validatorsElectedFor
	startElection = startWorkTime - electionsStartBefore
	endElection = startWorkTime - electionsEndBefore
	startNextElection = startElection + validatorsElectedFor

	# bla bla bla
	data = dict()
	data["electionId"] = startWorkTime
	data["tpsAvg"] = tpsAvg
	data["totalValidators"] = totalValidators
	data["onlineValidators"] = onlineValidators
	data["shardsNumber"] = shardsNumber
	data["validatorStatus"] = validatorStatus
	data["complaintsNumber"] = complaintsNumber

	data["validatorIndex"] = validatorIndex
	data["validatorEfficiency"] = validatorEfficiency
	data["adnlAddr"] = adnlAddr
	if validatorWallet is not None:
		data["validatorWalletAddr"] = validatorWallet.addrB64
		data["validatorWalletBalance"] = validatorAccount.balance
	data["loadavg"] = loadavg
	data["netLoadAvg"] = netLoadAvg
	data["mytoncoreStatus"] = mytoncoreStatus


	data["fullConfigAddr"] = fullConfigAddr
	data["fullElectorAddr"] = fullElectorAddr
	data["validatorsElectedFor"] = validatorsElectedFor
	data["electionsStartBefore"] = electionsStartBefore
	data["electionsEndBefore"] = electionsEndBefore
	data["stakeHeldFor"] = stakeHeldFor
	data["minStake"] = minStake
	data["maxStake"] = maxStake

	data["startValidation"] = startValidation
	data["endValidation"] = endValidation
	data["startElection"] = startElection
	data["endElection"] = endElection
	data["startNextElection"] = startNextElection
	return data
#end define

@dispatcher.add_method
def getSystemLoad():
	global ip
	ip.CheckAccess()
	data = dict()
	data["diskSpace"] = psutil.disk_usage('/')
	data["temp"] = psutil.sensors_temperatures()
	data["memory"] = psutil.virtual_memory()
	data["cpu_freq"] = psutil.cpu_freq()
	data["cpu_load"] = psutil.cpu_percent(interval=1)
	data["cpu_average"] = psutil.getloadavg()
	statistics = ton.GetSettings("statistics")
	data["disksLoadAvg"] = ton.GetStatistics("disksLoadAvg", statistics)
	data["disksLoadPercentAvg"] = ton.GetStatistics("disksLoadPercentAvg", statistics)
	return data
#end define

@dispatcher.add_method
def seqno(walletName):
	global ip
	ip.CheckAccess()
	wallet = ton.GetLocalWallet(walletName)
	seqno = ton.GetSeqno(wallet)
	return seqno
#end define

@dispatcher.add_method
def getconfig(configId):
	global ip
	ip.CheckAccess()
	data = ton.GetConfig(configId)
	return data
#end define
'''
@dispatcher.add_method
def nw(walletName, workchain=0):
	global ip
	ip.CheckAccess()
	wallet = ton.CreateWallet(walletName, workchain)
	return wallet.__dict__
#end define

@dispatcher.add_method
def aw(walletName):
	global ip
	ip.CheckAccess()
	wallet = ton.GetLocalWallet(walletName)
	if not os.path.isfile(wallet.bocFilePath):
		#raise JSONRPCDispatchException(208, f"Wallet {walletName} already activated")
		return False
	ton.ActivateWallet(wallet)
	return True
#end define
'''
@dispatcher.add_method
def wl():
	global ip
	ip.CheckAccess()
	data = dict()
	wallets = ton.GetWallets()
	for wallet in wallets:
		account = ton.GetAccount(wallet.addrB64)
		buff = dict()
		buff["name"] = wallet.name
		buff["addr"] = wallet.addrB64
		buff["workchain"] = wallet.workchain
		buff["status"] = account.status
		buff["balance"] = account.balance
		data[wallet.name] = buff
	return data
#end define

@dispatcher.add_method
def vas(addr):
	global ip
	ip.CheckAccess()
	account = ton.GetAccount(addr)
	return account.__dict__
#end define

@dispatcher.add_method
def vah(addr, limit):
	global ip
	ip.CheckAccess()
	account = ton.GetAccount(addr)
	history = ton.GetAccountHistory(account, limit)
	return history
#end define

@dispatcher.add_method
def ol():
	global ip
	ip.CheckAccess()
	offers = ton.GetOffers()
	return offers
#end define

@dispatcher.add_method
def el():
	global ip
	ip.CheckAccess()
	entries = ton.GetElectionEntries()
	return entries
#end define

@dispatcher.add_method
def ve():
	global ip
	ip.CheckAccess()
	Elections(ton)
	return True
#end define

@dispatcher.add_method
def vl():
	global ip
	ip.CheckAccess()
	validators = ton.GetValidatorsList()
	return validators
#end define

@dispatcher.add_method
def cl():
	global ip
	ip.CheckAccess()
	complaints = ton.GetComplaints()
	return complaints
#end define

@dispatcher.add_method
def get(name):
	global ip
	ip.CheckAccess()
	result = ton.GetSettings(name)
	return result
#end define

@dispatcher.add_method
def GetLastBlock():
	block = ton.GetLastBlock()
	return block
#end define

@dispatcher.add_method
def GetShards(block):
	shards = ton.GetShards(block)
	return shards
#end define

@dispatcher.add_method
def GetTransactions(block):
	transactions = ton.GetTransactions(block)
	return transactions
#end define

@dispatcher.add_method
def GetTrans(trans):
	messages = ton.GetTrans(trans)
	return messages
#end define


@dispatcher.add_method
def CheckUpdates():
	gitPath1 = srcDir + "mytonctrl/"
	gitPath2 = srcDir + "mtc-jsonrpc/"
	result1 = CheckGitUpdate(gitPath1)
	result2 = CheckGitUpdate(gitPath2)
	result = [result1, result2]
	return result
#end define
'''
@dispatcher.add_method
def UpdateMtc(args):
	global ip
	ip.CheckAccess()
	runArgs = ["bash", "/usr/src/mytonctrl/scripts/update.sh"]
	runArgs = SetArgsByArgs(runArgs, args)
	exitCode = run_as_root(runArgs)
	if exitCode == 0:
		text = "Update - {green}OK{endc}"
	else:
		text = "Update - {red}Error{endc}"
	return text;
	local.Exit()
#end define

@dispatcher.add_method
def UpdateJR(args):
	global ip
	ip.CheckAccess()
	runArgs = ["bash", "/usr/src/mtc-jsonrpc/update.sh"]
	runArgs = SetArgsByArgs(runArgs, args)

	exitCode = run_as_root(runArgs)
	if exitCode == 0:
		text = "Update - {green}OK{endc}"
	else:
		text = "Update - {red}Error{endc}"
	return text;
	local.Exit()
#end define
'''

@dispatcher.add_method
def GetOTPStatus():
	global ip
	ip.CheckAccess()
	return ton.GetSettings("jsonrpcOTP")
#end define

@dispatcher.add_method
def SetupOTP():
	global ip
	ip.CheckAccess()
	local.add_log("start SetupOTP function", "debug")
	otpStatus = ton.GetSettings("jsonrpcOTP")
	if otpStatus:
		return "OTP already configured"
	else:
		secretKey = pyotp.random_base32()
		ton.SetSettings("jsonrpcOTPSecret", secretKey)
		QRcode = pyotp.totp.TOTP(secretKey).provisioning_uri(name='TonAdmin.org')
		return [QRcode, secretKey]
#end define

@dispatcher.add_method
def VerifyOTP(code):
	global ip
	ip.CheckAccess()
	otpStatus = ton.GetSettings("jsonrpcOTP")
	if otpStatus:
		return "OTP already configured"
	else:
		OTPSecret = ton.GetSettings("jsonrpcOTPSecret")
		totp = pyotp.TOTP(OTPSecret)
		print("Current OTP:", totp.now())
		if totp.now() == code:
			ton.SetSettings("jsonrpcOTP", True)
			return True
		else:
			return False
#end define

def GetPort():
	port = ton.GetSettings("jsonrpcPort")
	if port is None:
		port = random.randint(2000, 65000)
		ton.SetSettings("jsonrpcPort", port)
	return port
#end define


def SetArgsByArgs(runArgs, args):
	if len(args) == 1:
		buff = args[0]
		if "https://" in buff:
			runArgs += ["-r", buff]
		else:
			runArgs += ["-b", buff]
	elif len(args) == 2:
		runArgs += ["-r", args[0]]
		runArgs += ["-b", args[1]]
	return runArgs
#end define

def SetWebPassword():
	local.add_log("start SetWebPassword function", "debug")
	port = GetPort()
	ip = requests.get("https://ifconfig.me").text
	url = "https://{ip}:{port}/".format(ip=ip, port=port)
	signal.alarm(10)
	passwd = getpass.getpass("Set a new password for the web admin panel: ")
	signal.alarm(0)
	signal.alarm(10)
	repasswd = getpass.getpass("Repeat password: ")
	signal.alarm(0)
	if passwd != repasswd:
		print("Error: Password mismatch")
		return
	passwdHash = generate_password_hash(passwd)
	ton.SetSettings("passwdHash", passwdHash)

	scraper = cloudscraper.create_scraper()
	r = scraper.get("https://tonadmin.org/ip.json").text
	data_json = json.loads(r)
	allowedIP = data_json[0]

	ip = "0.0.0.0"
	sslKeyPath = local.buffer.my_work_dir + "ssl"
	crtPath = sslKeyPath + ".crt"
	keyPath = sslKeyPath + ".key"

	if os.path.isfile(keyPath) == False:
		make_ssl_devcert(sslKeyPath, host=ip)
	#end if

	runArgs = ["bash", srcDir + "mtc-jsonrpc/setupProxy.sh", str(allowedIP), str(port), local.buffer.my_work_dir]
	exitCode = run_as_root(runArgs)

	print("Configuration complete.")
	print("Now you can go to https://tonadmin.org")
	print("and use the following data:")
	print("--------------------------------------")
	print("Validator URL:", url)
	print("--------------------------------------")
#end define


def Init():
	# Event reaction
	if ("-p" in sys.argv):
		SetWebPassword()
		return
	#end if

	if not ton.GetSettings("passwdHash"):
		SetWebPassword()
		return
	#end if

	port = GetPort()
	# Event reaction
	if ("-port" in sys.argv):
		port = int(sys.argv[2])
	#end if

	hostip = "127.0.0.1"

	ip = "0.0.0.0"
	sslKeyPath = local.buffer.my_work_dir + "ssl"
	crtPath = sslKeyPath + ".crt"
	keyPath = sslKeyPath + ".key"

	if os.path.isfile(keyPath) == False:
		make_ssl_devcert(sslKeyPath, host=ip)
	#end if

	run_simple(hostip, port-1, application)
#end define


###
### Старт программы
###

if __name__ == "__main__":
	signal.signal(signal.SIGALRM, timeout)
	Init()
#end if
