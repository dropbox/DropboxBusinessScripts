#!/usr/bin/python
# -*- ccoding: utf-8 -*-

import json
import requests
import pprint                         # Allows Pretty Print of JSON
import os                             # Allows for the clearing of the Terminal Window
import csv                            # Allows outputting to CSV file
import time, datetime
import sys
import logging

"""
Script to list all applications linked to the team members' accounts.
Note, this script/endpoint does not list any team-linked applications.

Scripts loads all Team Members to allow reporting on email address and linked apps. 
Script loads all apps and prints to a file at the same location as execution of script.

It will generate one file:
- <datetime>linked_member_apps.csv


Requirements:
  Script tested on Python 3.6.5

  One Dropbox API Token is needed, inserted just below this comments section.
  Permissions needed on token:
  - account_info.read   "View basic information about your Dropbox account such as your username, email, and country"
  - team_data.member    "View structure of your team's and members' folders"
  - members.read        "View your team membership"
  - sessions.list       "View your team's sessions, devices, and apps"


Pre-requisites:
* Scripts requires library 'Requests' - You can install using "pip install requests"

"""





"""
Set your OAuth Tokens here
"""

gToken =  ''    	# Scoped API Token  




"""##########################################################################################
                               DO NOT EDIT BELOW THIS POINT
##########################################################################################"""

gTotalTimeStart = datetime.datetime.fromtimestamp(time.time())


#############################################
# Function to print Message to console in a tidy box
#############################################
def printmessageblock( str ):
  print ("\n*********************************************************")
  print ("* %s" % (str))
  print ("*********************************************************\n")
  return;

#############################################
# Function to return current Timestamp 
#############################################
def getTimeYMDHM():
  lRightNow = datetime.datetime.fromtimestamp(time.time()).strftime('%y%m%d-%H-%M') 
  return lRightNow;

#############################################
# Function to return Message to console in a tidy box
#############################################
def getTimeInHoursMinutesSeconds( sec ):
    return time.strftime("%H hrs %M mins %S sec", time.gmtime(sec))



"""
#############################################
# Step 1
# 1. Setup the necessary variables to get list of members. 
#############################################
"""
aHeaders = {'Content-Type': 'application/json', 'Authorization': 'Bearer %s' % gToken}
aURL = 'https://api.dropboxapi.com/2/team/members/list'
aData = json.dumps({'limit': 300}) 




"""
#############################################
# Step 2
# 1. Get list of all Dropbox Team Members
# 2. Create in memory list of them.
#############################################
"""
hasMore = True;      # Controls how long we stay in while loop loading users. 
loopCounter = 0      # Count of how many times we hit the API 
dbxUsers = []        # List of Dropbox Users
dbxEmailLookup = {}  # A quick reference list of key-pair values of team-member-ids and email addressses 

print ("> Retrieving Dropbox Users via API")
timestart = datetime.datetime.fromtimestamp(time.time())			# Used to note start and calculare total time script took to run.

while hasMore:

	print (">>> API call")
	""" Make the API call """ 
	aResult = requests.post(aURL, headers=aHeaders, data=aData)

	print ("<<< Results")

	# If we don't get a 200 HTML response code, we didn't get a result. 
	if( aResult.status_code != 200 ):
		print ('>>> Failed to get a response to call for /team/members/list')
		logging.info( aResult.text ) 
		print (aResult.text)
		exit();

	# Note the JSON response
	members = aResult.json()

	# Iterate over the Members in the JSON
	for aMember in members['members']:
		dbxUsers.append( aMember )
		dbxEmailLookup[ aMember['profile']['team_member_id'] ] = aMember['profile']['email'] 

	hasMore = members['has_more']            # Note if there's another cursor call to make. 

	# If it's the first run, from this point onwards the API call is the /continue version.
	if ( loopCounter >= 0 ):
		aURL = 'https://api.dropboxapi.com/2/team/members/list/continue'
		aData = json.dumps({'cursor': members['cursor']}) 
		loopCounter += 1

# How long did the APIs take?
timestop = datetime.datetime.fromtimestamp(time.time())
strMessage = "We have the Dropbox users in memory from " + str(loopCounter) + " API Calls. it took " + str((timestop-timestart).total_seconds()) + " seconds."
print ( strMessage )
logging.info( strMessage )



"""
#############################################
# Step 3
# 1. Get all Linked Apps  
#############################################
"""

aHeaders = {'Content-Type': 'application/json', 'Authorization': 'Bearer %s' % gToken}
aURL = 'https://api.dropboxapi.com/2/team/linked_apps/list_members_linked_apps'
aData = json.dumps(None) 

hasMore = True;      # Controls how long we stay in while loop 
loopCounter = 0      # Count of how many times we hit the API 


print ("> Retrieving Dropbox Users via API")
timestart = datetime.datetime.fromtimestamp(time.time())			# Used to note start and calculare total time script took to run.



fileName = ("%s_" + "linked_member_apps.csv") % getTimeYMDHM()


with open( fileName, 'w') as csvfile:
	writer = csv.writer(csvfile, delimiter=',')
	# Write the Column Headers
	writer.writerow(['Email address', 'App ID', 'App Name', 'Linked Date'])


	while hasMore:

		print (">>> API call")
		""" Make the API call """ 
		aResult = requests.post(aURL, headers=aHeaders, data=aData)

		print ("<<< Results")

		# If we don't get a 200 HTML response code, we didn't get a result. 
		if( aResult.status_code != 200 ):
			print ('>>> Failed to get a response to call for /2/team/linked_apps/list_members_linked_apps')
			logging.info( aResult.text ) 
			print (aResult.text)
			exit();

		# Note the JSON response
		memberLinkedApps = aResult.json()

		# Iterate over the Members in the JSON
		for aLinkedApp in memberLinkedApps['apps']:
			userEmailAddress = dbxEmailLookup.get( aLinkedApp['team_member_id'] )   # Get team members email address
			print ( "processing: " + userEmailAddress )
			logging.info( "processing: " + userEmailAddress )


			linked_api_apps = aLinkedApp['linked_api_apps']

			for app in linked_api_apps:
				writer.writerow([userEmailAddress, app['app_id'], app['app_name'], app['linked']])

		hasMore = memberLinkedApps['has_more']            # Note if there's another cursor call to make. 

		# If it's the first run, from this point onwards the API call is the /continue version.
		if ( loopCounter >= 0 ):
			if ( hasMore ):
				aData = json.dumps({'cursor': memberLinkedApps['cursor']}) 
			loopCounter += 1

	# How long did the APIs take?
	timestop = datetime.datetime.fromtimestamp(time.time())
	strMessage = "We have the Dropbox users in memory from " + str(loopCounter) + " API Calls. it took " + str((timestop-timestart).total_seconds()) + " seconds."
	print ( strMessage )
	logging.info( strMessage )





"""
#############################################
# Step 2
# 1. Output how long the script took to run.
#############################################
"""
gTotalTimeStop = datetime.datetime.fromtimestamp(time.time())
gTotalTimeInSeconds = (gTotalTimeStop-gTotalTimeStart).total_seconds()
timeAsStr = getTimeInHoursMinutesSeconds( gTotalTimeInSeconds )
printmessageblock( " Script finished running, it took %s seconds." % ( timeAsStr ) )
