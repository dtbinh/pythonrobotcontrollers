#!/usr/bin/python
import time
import math
import socket
import pymongo
from pymongo import MongoClient

JOYSTICK_MAX_MODULUS = 100
MAX_SPEED = 100
TURN_MULTIPLIER = 0.4
ROBOT_RADIUS_MM = 27

# signal handler setup
import signal
import sys


def signal_handler(signal, frame):
    sys.exit()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
# end signal handler setup

# MongoDB setup
mongoclient = MongoClient()
db = mongoclient.hrui
data = db.data
# end MongoDB setup

# socket setup
HOST, PORT = "192.168.141.100", 1000
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))
# end socket setup


def setSpeeds(x, y, lockMode):
    leftSpeed = 0
    rightSpeed = 0
    speedModulus = math.sqrt(x*x + y*y)*MAX_SPEED/JOYSTICK_MAX_MODULUS
    if lockMode == "lock2ways" or lockMode == "lock4ways":
        if y == 0:
            if x < 0:
                leftSpeed = -speedModulus*TURN_MULTIPLIER
                rightSpeed = speedModulus*TURN_MULTIPLIER
            elif x > 0:
                leftSpeed = speedModulus*TURN_MULTIPLIER
                rightSpeed = -speedModulus*TURN_MULTIPLIER
        elif x == 0:
            if y > 0:
                leftSpeed = speedModulus
                rightSpeed = speedModulus
            elif y < 0:
                leftSpeed = -speedModulus
                rightSpeed = -speedModulus
        return round(leftSpeed, 2), round(rightSpeed, 2)
    return 0, 0


def correctPos(buf, leftPos, rightPos, x, y, alpha):
    # parse new encoder position from string
    newLeftPos, newRightPos = tuple(buf.split(';'))
    newLeftPos, newRightPos = float(newLeftPos), float(newRightPos)
    # get increments, update encoder pos
    Aleft, Aright = newLeftPos - leftPos, newRightPos - rightPos
    leftPos, rightPos = newLeftPos, newRightPos
    # check for encoder glitch
    if ((math.fabs(Aleft) > 5) or (math.fabs(Aright) > 5)):
        # bogus encoder leap in reading, adjust and return.
        return x, y, alpha, leftPos, rightPos

    # turning left
    if (Aleft < 0 and Aright > 0):
        alpha = alpha + (-Aleft + Aright) / (2 * ROBOT_RADIUS_MM)
    # turning right
    elif (Aleft > 0 and Aright < 0):
        alpha = alpha - (Aleft - Aright) / (2 * ROBOT_RADIUS_MM)
    # going forward
    else:
        x = x + (Aleft + Aright)*math.cos(alpha)/2
        y = y + (Aleft + Aright)*math.sin(alpha)/2
    # enforce 0 < alpha < 2*pi
    if alpha > 2*math.pi:
        alpha = alpha - 2*math.pi
    elif alpha < 0:
        alpha = 2*math.pi + alpha

    return round(x, 4), round(y, 4), round(alpha, 4), leftPos, rightPos

# define start position and orientation
x, y = 0, 0
alpha = math.pi/2
leftPos, rightPos = 0, 0
# Main Loop
while True:
    # get joystick position and mode
    joystick = data.find_one({"_id": 0})
    joyx = round(float(joystick['x']), 2)
    joyy = round(float(joystick['y']), 2)
    lockMode = str(joystick['mode'])
    gamepad = data.find_one({"item": "gamepad"})
    lx = 100*float(gamepad['axes'][0])
    ly = -100*float(gamepad['axes'][1])
    if math.fabs(ly) > math.fabs(lx):
    	lx = 0
    else:
    	ly = 0
    # generate speeds based on joystick
    (leftSpeed, rightSpeed) = setSpeeds(lx, ly, "lock4ways")
    # send speeds to khepera
    s.send(str(leftSpeed)+";"+str(rightSpeed))
    # receive encoder position in mm from khepera
    buf = s.recv(1024)
    x, y, alpha, leftPos, rightPos = correctPos(
        buf, leftPos, rightPos, x, y, alpha)
    # print(str(alpha))
    # update DB with position data
    data.update({"item": "robotData"}, {
                "$set": {"position": {"x": x, "y": y}, "orientation": {"alpha": alpha}}})
