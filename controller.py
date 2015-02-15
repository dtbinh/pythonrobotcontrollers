#!/usr/bin/python
import os
import time
import signal
import sys
import math
import vrep
import pymongo
import subprocess
from pymongo import MongoClient

PI = 3.1416
JOYSTICK_MAX_MODULUS = 90
MAX_SPEED = 3*PI
DEGREE_PRECISION = 1
TURN_MULTIPLIER = 0.2




def close():
	vrepSim(clientID,"stop")
	vrep.simxFinish(clientID)
	vrep.simxFinish(-1)
	print("Program Exit")
	sys.exit(0)

def signal_handler(signal, frame):
	close()	

def vrepSim(clientID, action):
	vrep.simxFinish(-1)
	localhost = "127.0.0.1"
	clientID=vrep.simxStart(localhost,19997,True,True,1000,5)
	if clientID!=-1:
		print('Connected to remote API server')
		if action=="start":
			err = vrep.simxStartSimulation(clientID,vrep.simx_opmode_oneshot_wait)
			if (not err):
				print('Sim Started')
		elif action=="stop":
			err = vrep.simxStopSimulation(clientID,vrep.simx_opmode_oneshot_wait)
			if (not err):
				print('Sim Stopped')		
		print("Disconnected from remote API server")
	else:
		print('Failed connecting to remote API server')
	vrep.simxFinish(clientID)
	return clientID

def vrepConnect(clientID, port):
	clientID=vrep.simxStart('127.0.0.1',port,True,True,1000,5)
	if clientID!=-1:
		print("Open Connection on port:"+str(port)+' with clientID: '+str(clientID))
	else: 
		print("Failed connecting through port:"+str(port))
		vrep.simxFinish(clientID)
	return clientID

def setSpeeds(x, y, angleModel, lockMode):
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
	if joystickAlpha<0:
		joystickAlpha = round(2*PI-abs(joystickAlpha),DEGREE_PRECISION)

	if round(angleModel[2], DEGREE_PRECISION) >= 2*PI:
		angleModel[2] = 0
	targetAlpha = round(angleModel[2],DEGREE_PRECISION)

	if y>=0:
		velizq = speedModulus
		velder = speedModulus
	elif y<0:
		velizq = -speedModulus
		velder = -speedModulus
		joystickAlpha = round(joystickAlpha - PI,DEGREE_PRECISION)
	
	if targetAlpha<joystickAlpha:
		velizq = -speedModulus*TURN_MULTIPLIER
		velder = speedModulus*TURN_MULTIPLIER
		angleModel[2] += abs(angleModel[0]-angleModel[1])

	elif targetAlpha>joystickAlpha:
		velizq = speedModulus*TURN_MULTIPLIER
		velder = -speedModulus*TURN_MULTIPLIER
		angleModel[2] -= abs(angleModel[0]-angleModel[1])

	angleModel[1] = angleModel[0]

	return velizq, velder, targetAlpha==joystickAlpha,

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# subprocess.Popen(["vrep", "longtask.py"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
# time.sleep(10)

mongoclient = MongoClient()
db = mongoclient.hrui
data = db.data

clientID = 0
clientID = vrepSim(clientID,"start")

clientID = vrepConnect(clientID,20001)

if clientID!=-1:
	count = 0
	velizq= 0
	velder= 0
	oldPosition = [0,0,0]
	oldOrientation = [0,0,0]
	oldSpeed = [0,0,0]
	oldAngularSpeed = [0,0,0]
	angleModel = [0,0,0]
	targetReached = False
	speedMod = 1
	(err, robot) = vrep.simxGetObjectHandle(clientID,"K3_robot",vrep.simx_opmode_oneshot_wait)
	(err, rwmotor) = vrep.simxGetObjectHandle(clientID,"K3_rightWheelMotor#",vrep.simx_opmode_oneshot_wait)
	(err, lwmotor) = vrep.simxGetObjectHandle(clientID,"K3_leftWheelMotor#",vrep.simx_opmode_oneshot_wait)
	
	oldJoystick = data.find_one({"item": "joystick"})
	while angleModel[1]==0:
		(err, orientation) = vrep.simxGetObjectOrientation(clientID,robot,-1,vrep.simx_opmode_oneshot)
		angleModel[1]= orientation[1]
	angleModel[2] = abs(angleModel[1])
	
	while clientID!=-1:	
		joystick = data.find_one({"_id": 0})
		x = float(joystick['x'])
		y = float(joystick['y'])
		lockMode = str(joystick['mode'])
		(err, position) = vrep.simxGetObjectPosition(clientID,robot,-1,vrep.simx_opmode_oneshot)
		(err, orientation) = vrep.simxGetObjectOrientation(clientID,robot,-1,vrep.simx_opmode_oneshot)
		(err, speed, angularSpeed) = vrep.simxGetObjectVelocity(clientID,robot,vrep.simx_opmode_oneshot)
		angleModel[0] = orientation[1]
		(velizq, velder, targetReached) = setSpeeds(x, y, angleModel, lockMode)
		if (joystick != oldJoystick) or targetReached:			
			oldJoystick = joystick	
			#print('x: '+str(x)+' y: '+str(y)+' vel: izq '+str(velizq)+' der '+str(velder)+' Lock Mode: '+str(lockMode))
			vrep.simxSetJointTargetVelocity(clientID,lwmotor,velizq,vrep.simx_opmode_oneshot)
			vrep.simxSetJointTargetVelocity(clientID,rwmotor,velder,vrep.simx_opmode_oneshot)
			
		if (position != oldPosition): 
			data.update({"item": "robotData"}, {"$set":{"position": {"x": round(position[0],4), "y": round(position[1],4), "z": round(position[2],4)}}})
			oldPosition = position
		if (orientation!= oldOrientation):
			data.update({"item": "robotData"}, {"$set":{"orientation": {"alpha": round(math.degrees(orientation[0]),2), "beta": round(math.degrees(orientation[1]),2), "gamma": round(math.degrees(orientation[2]),2)}}})
			oldOrientation = orientation
		if (speed!= oldSpeed):
			data.update({"item": "robotData"}, {"$set":{"speed": {"vx": round(speed[0],2), "vy": round(speed[1],2), "vz": round(speed[2],2)}}})
			oldSpeed = speed
		if (angularSpeed!= oldAngularSpeed):			
			data.update({"item": "robotData"}, {"$set":{"angularSpeed": {"dAlpha": round(angularSpeed[0],2), "dBeta": round(angularSpeed[1],2), "dGamma": round(angularSpeed[2],2)}}})
			oldAngularSpeed = angularSpeed
		
		#Check connection
		if vrep.simxGetConnectionId(clientID)==-1:
			count += 1
		if count>2:
			break
			
close()		


