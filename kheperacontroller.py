#!/usr/bin/python
import os
import time
import signal
import sys
import math
import socket
import pymongo
from pymongo import MongoClient

PI = 3.1416
JOYSTICK_MAX_MODULUS = 90
MAX_SPEED = 3*PI
DEGREE_PRECISION = 1
TURN_MULTIPLIER = 0.2




def signal_handler(signal, frame):
	pass
	sys.exit()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def setSpeeds(x, y, lockMode):
	velizq = 0
	velder = 0
	speedModulus = math.sqrt(x*x + y*y)*MAX_SPEED/JOYSTICK_MAX_MODULUS
	joystickAlpha = round(math.atan2(y,x),DEGREE_PRECISION)
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
		return velizq, velder, True,

mongoclient = MongoClient()
db = mongoclient.hrui
data = db.data

HOST, PORT = "192.168.141.100", 1001
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))
velizq = 0
velder = 0

while True:	
	joystick = data.find_one({"_id": 0})
	x = float(joystick['x'])
	y = float(joystick['y'])
	lockMode = str(joystick['mode'])
	if x<0:
		s.send("a")
	elif x>0:
		s.send("d")
	if y>0:
		s.send("w")
	elif y<0:
		s.send("s")
	if x==0 and y==0:
		s.send("p")
	time.sleep(0.1)


