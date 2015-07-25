import sys
import time
import random
import math
sys.path.append("crazyflie/lib")

import cflib.crtp
from cflib.crazyflie import Crazyflie
from threading import Thread
import logging
import pymongo
from pymongo import MongoClient

crazyflie = Crazyflie()


# MongoDB setup
mongoclient = MongoClient()
db = mongoclient.hrui
data = db.data
# end MongoDB setup

logging.basicConfig(level=logging.ERROR)
cflib.crtp.init_drivers(enable_debug_driver=False)


def connected(link_uri):
    print "Connected"
    gamepad()


def connection_failed(link_uri, msg):
    print "Connection failed"


def connection_lost(link_uri, msg):
    print "Connection lost"


def disconnected(link_uri):
    print "Disconnected"

def test():
    while True:
        gamepad = data.find_one({"item": "gamepad"})
        print(gamepad)
        time.sleep(0.5)

def motion():
    i = 0
    while True:
        roll = 0
        pitch = 0
        yaw = 0
        thrust = 0
        deviceData = data.find_one({"item": "deviceData"})
        if deviceData['devOrientation']['beta'] is not None:
            thrust = float(deviceData['devOrientation']['beta'])
        else:
            thrust = 0
        if thrust < 10:
            thrust = 0
        thrust = min(thrust, 90)
        thrust = 10000 + thrust*50000/80
        thrust = min(thrust, 65000)
        crazyflie.commander.send_setpoint(roll, pitch, yaw, thrust)
        print(i)
        i = i+1


def gamepad():
    i = 0
    roll = 0
    pitch = 0
    yaw = 0
    thrust = 0
    while True:
        if i > 2:
            voiceCommand = data.find_one({"item": "voiceCommand"})
            gamepad = data.find_one({"item": "gamepad"})
            if (voiceCommand['value'] == 'stop' or int(gamepad['buttons'][9]) == 1):
                land(thrust)
                crazyflie.close_link()
            lx = float(gamepad['axes'][0])
            ly = -float(gamepad['axes'][1])
            rx = float(gamepad['axes'][2])
            ry = -float(gamepad['axes'][3])
            if ry < 0.10:
                ry = 0
            if math.fabs(ly) < 0.10:
                ly = 0
            if math.fabs(lx) < 0.10:
                lx = 0
            if math.fabs(rx) < 0.10 or math.fabs(ry) >= 0.6:
                rx = 0
            thrust = 10000 + ry * 50000
            roll = lx * 30
            pitch = ly * 30
            yaw = rx * 200
            print(thrust)
            crazyflie.commander.send_setpoint(roll, pitch, yaw, thrust)
            time.sleep(0.05)
        i = i+1


def land(thrust):
    while thrust > 10000:
        thrust = thrust/1.2
        crazyflie.commander.send_setpoint(0, 0, 0, thrust)
        time.sleep(0.5)
    crazyflie.close_link()


print "Scanning interfaces for Crazyflies..."
available = cflib.crtp.scan_interfaces()
if len(available) >= 1:
    print "Crazyflies found:"
    print str(available)
    link = available[0][0]
    for i in xrange(1, len(available)):
        if "80" in available[i][0]:
            link = available[i][0]
    print("Connecting to:" + link)
    crazyflie.connected.add_callback(connected)
    crazyflie.disconnected.add_callback(disconnected)
    crazyflie.connection_failed.add_callback(connection_failed)
    crazyflie.connection_lost.add_callback(connection_lost)
    crazyflie.open_link(link)
else:
    print "No Crazyflies found"
