#!/usr/bin/python
import time
import signal
import sys
import math
import socket
import pymongo
from pymongo import MongoClient

JOYSTICK_MAX_MODULUS = 90
MAX_SPEED = 100
TURN_MULTIPLIER = 0.4



#signal handler setup
def signal_handler(signal, frame):
	pass
	sys.exit()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
#end signal handler setup

#MongoDB setup
mongoclient = MongoClient()
db = mongoclient.hrui
data = db.data
#end MongoDB setup

#socket setup
HOST, PORT = "192.168.141.100", 1000
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))
#end socket setup

def setSpeeds(x, y, lockMode):
	velizq = 0
	velder = 0
	speedModulus = math.sqrt(x*x + y*y)*MAX_SPEED/JOYSTICK_MAX_MODULUS
	if lockMode=="lock2ways" or lockMode=="lock4ways":
		if y==0:
			if x<0:
				velizq = -speedModulus*TURN_MULTIPLIER
				velder = speedModulus*TURN_MULTIPLIER	
			elif x>0:
				velizq = speedModulus*TURN_MULTIPLIER
				velder = -speedModulus*TURN_MULTIPLIER
		elif x==0:
			if y>0:
				velizq = speedModulus
				velder = speedModulus
			elif y<0:
				velizq = -speedModulus
				velder = -speedModulus
		return velizq, velder
	return 0, 0

#Main Loop
while True:	
	joystick = data.find_one({"_id": 0})
	joyx = round(float(joystick['x']),2)
	joyy = round(float(joystick['y']),2)
	lockMode = str(joystick['mode'])
	(velizq, velder) = setSpeeds(joyx, joyy, lockMode)
	s.send(str(round(velizq,2))+";"+str(round(velder,2)))
	buf = s.recv(1024)
	x, y = tuple(buf.split(';'))
	x, y = float(x), float(y)
	print(str(x)+";"+str(y))
	data.update({"item": "robotData"}, {"$set":{"position": {"x": round(x,4), "y": round(y,4)}}})