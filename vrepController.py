#!/usr/bin/python
import os
import time
import signal
import sys
import math
import vrep
from pymongo import MongoClient

PI = 3.1416
JOYSTICK_RESOLUTION = 0.01
JOYSTICK_MAX_MODULUS = 80
MAX_SPEED = 1*PI
TURN_SPEED_MODIFIER = 0.3
DEGREE_PRECISION = 1


def close():
	vrepSim(clientID,"stop")
	vrep.simxFinish(clientID)
	vrep.simxFinish(-1)
	sys.exit(0)

def signal_handler(signal, frame):
	close()	

def vrepSim(clientID, action):
	vrep.simxFinish(-1)
	clientID=vrep.simxStart('127.0.0.1',19997,True,True,5000,5)
	if clientID!=-1:
		print 'Connected to remote API server'
		if action=="start":
			err = vrep.simxStartSimulation(clientID,vrep.simx_opmode_oneshot_wait)
			if (not err):
				print 'Sim Started'
		elif action=="stop":
			err = vrep.simxStopSimulation(clientID,vrep.simx_opmode_oneshot_wait)
			if (not err):
				print 'Sim Stopped'
		vrep.simxFinish(clientID)
		print "Disconnected from remote API server"
	else:
		print 'Failed connecting to remote API server'

def vrepConnect(clientID, port):
	clientID=vrep.simxStart('127.0.0.1',port,True,True,5000,5)
	if clientID!=-1:
		print "Open Connection on port:"+str(port)

def setSpeeds(x, y, alpha, oldAlpha, absAlpha, clientID, robot, lwmotor, rwmotor):
	velizq = 0
	velder = 0
	speedModulus = math.sqrt(x*x + y*y)*MAX_SPEED/JOYSTICK_MAX_MODULUS

	joystickAlpha = round(math.atan2(y,x),DEGREE_PRECISION)

	if joystickAlpha<0:
		joystickAlpha = round(2*PI-abs(joystickAlpha),DEGREE_PRECISION)

	if round(absAlpha, DEGREE_PRECISION) >= 2*PI:
		absAlpha = 0
	targetAlpha = round(absAlpha,DEGREE_PRECISION)

	if y>=0:
		velizq = speedModulus
		velder = speedModulus
	elif y<0:
		velizq = -speedModulus
		velder = -speedModulus
		joystickAlpha = round(joystickAlpha - PI,DEGREE_PRECISION)
	
	if targetAlpha==joystickAlpha:
		x = x + JOYSTICK_RESOLUTION

	elif targetAlpha<joystickAlpha:

		velizq = -speedModulus*TURN_SPEED_MODIFIER
		velder = speedModulus*TURN_SPEED_MODIFIER
		absAlpha = absAlpha + abs(alpha-oldAlpha)

	elif targetAlpha>joystickAlpha:

		velizq = speedModulus*TURN_SPEED_MODIFIER
		velder = -speedModulus*TURN_SPEED_MODIFIER
		absAlpha = absAlpha - abs(alpha-oldAlpha)

	oldAlpha=alpha

	return velizq, velder, x, oldAlpha, absAlpha		


signal.signal(signal.SIGINT, signal_handler)

mongoclient = MongoClient()
db = mongoclient.hrui
data = db.data

clientID = 0
vrepSim(clientID,"start")


vrepConnect(clientID,20001)
time.sleep(1)
if clientID!=-1:
	
	velizq= 0
	velder= 0
	absAlpha = 0
	oldAlpha = 0
	(err, robot) = vrep.simxGetObjectHandle(clientID,"K3_robot",vrep.simx_opmode_oneshot_wait)
	(err, rwmotor) = vrep.simxGetObjectHandle(clientID,"K3_rightWheelMotor#",vrep.simx_opmode_oneshot_wait)
	(err, lwmotor) = vrep.simxGetObjectHandle(clientID,"K3_leftWheelMotor#",vrep.simx_opmode_oneshot_wait)
	
	joystick = data.find_one({"item": "joystick"})
	oldx = float(joystick['x'])
	oldy = float(joystick['y'])
	(err, oldPosition) = vrep.simxGetObjectPosition(clientID,robot,-1,vrep.simx_opmode_oneshot)
	while oldAlpha==0:
		(err, angles) = vrep.simxGetObjectOrientation(clientID,robot,-1,vrep.simx_opmode_oneshot)
		oldAlpha = angles[1]
	absAlpha = abs(oldAlpha)
	while True:	
		joystick = data.find_one()
		x = float(joystick['x'])
		y = float(joystick['y'])
		(err, angles) = vrep.simxGetObjectOrientation(clientID,robot,-1,vrep.simx_opmode_oneshot)
		(velizq, velder, x, oldAlpha, absAlpha) = setSpeeds(x, y, angles[1], oldAlpha, absAlpha, clientID, robot, lwmotor, rwmotor)
		if (x!=oldx) or (y!=oldy):
			oldx = x
			oldy = y						
			print 'x: '+str(x)+' y: '+str(y)+' vel: izq '+str(velizq)+' der '+str(velder)
			vrep.simxSetJointTargetVelocity(clientID,lwmotor,velizq,vrep.simx_opmode_oneshot)
			vrep.simxSetJointTargetVelocity(clientID,rwmotor,velder,vrep.simx_opmode_oneshot)
		(err, position) = vrep.simxGetObjectPosition(clientID,robot,-1,vrep.simx_opmode_oneshot)
		if position[0] != oldPosition[0]:
			data.update({"item": "position"}, {"$set":{"x": round(position[0],4), "y": round(position[1],4), "z": round(position[2],4)}})
			oldPosition = position
close()		


