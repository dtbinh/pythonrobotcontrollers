#!/usr/bin/python
from pymongo import MongoClient

def geolocationTest(i):
	i = i+1
	if (i==100):
		geolocation = data.find_one({"_id": 2})
		latitude = float(geolocation['latitude'])
		print(latitude)
		data.update({"item": "robotGeolocation"}, {"$set":{"latitude": latitude+0.0000001}})
		i=0
	return i
			
	
mongoclient = MongoClient()
db = mongoclient.hrui
data = db.data
i=0
while True:
	i = geolocationTest(i)

			
		


