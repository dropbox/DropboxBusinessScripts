#!/usr/bin/python
# -*- coding: latin-1 -*-

import json
import requests
import os                             # Allows for the clearing of the Terminal Window
import csv                            # Allows outputting to CSV file
import time, datetime
import sys


"""
The intention of this script is to:

- Iterate over all members of a team
- If team member has an 'external_id' attribute set on the member profile, we'll set it to ""

Requirements:
  Script writen and tested on Python 3.6.5

  Dropbox API Token needed needed inserted just below this comments section.
  * Team Member Management

Pre-requisites:
* Scripts requires library 'Requests' - You can install using "pip install requests"

"""




"""
Set your OAuth Token here
"""
gTokenTMM = ''    	# Team Member Management   

# Flag to control actually permanent wipe of 'external_id'. Defaults to MOCK run, whereby no change occurs.
gRunInTestMode = True






"""
********************************************************************************************************************
                                             DO NOT EDIT BELOW THIS POINT
********************************************************************************************************************
"""



#############################################
# Function to return current Timestamp 
#############################################
def getTimeYMDHM():
  lRightNow = datetime.datetime.fromtimestamp(time.time()).strftime('%y%m%d-%H-%M') 
  return lRightNow;

def getPrettyTime():
  lRightNow = datetime.datetime.fromtimestamp(time.time()).strftime('%H:%M:%S %d-%m-%Y') 
  return lRightNow;

#############################################
# Function to print Message to console in a tidy box
#############################################
def printmessageblock( str ):
  print ("\n*********************************************************")
  print ("* %s" % (str))
  print ("*********************************************************\n")
  return;


#############################################
# Function to print Message to console in a tidy box
#############################################
def getTimeInHoursMinutesSeconds( sec ):
    return time.strftime("%H hrs %M mins %S sec", time.gmtime(sec))

#############################################
# Function to wipe members 'external_id'
#############################################
def wipeExternalID(email, team_member_id):

	aURL = "https://api.dropboxapi.com/2/team/members/set_profile"
	aData = json.dumps({'user': { '.tag': 'team_member_id', 'team_member_id': str(team_member_id)}, 'new_external_id': ''})


	lHeadersTMFA = {'Content-Type': 'application/json',
		'Authorization': 'Bearer %s' % gTokenTMM} 

	aResult = None

	if (not gRunInTestMode):
		aResult = requests.post(aURL, headers=lHeadersTMFA, data=aData)  # Wipe 'external_id'
		print( "wiping external_id for '" + str(email) + "'")
	else:
		print ( "Testing call to wipe External ID for %s" % email )
		return True

	if( aResult.status_code != 200 ):
		print ( "ERROR: Failed to wipe External ID for email '%s', error code '%s', '%s'" % (email, aResult.status_code, aResult.text))
		return False

	return True


"""
# ############################################
# Step 0
# Clear the terminal window, not essential but makes it easier to read this way.
# ############################################
"""

os.system('cls' if os.name=='nt' else 'clear')

print ( "Starting: %s" % getPrettyTime() )
totalTimeStart = datetime.datetime.fromtimestamp(time.time())

if( gRunInTestMode ):
	print ( "******* MOCK RUN *******" )


"""
# ############################################
# Step 1 
# Get a list of all team members to locate the ones we've to change
# ############################################
"""
aHeaders = {'Content-Type': 'application/json', 'Authorization': 'Bearer %s' % gTokenTMM}
aURL = 'https://api.dropboxapi.com/2/team/members/list'
aData = json.dumps({'limit': 50, 'include_removed': True}) 

hasMore = True;
loopCounter = 0;
totalMembers = 0

while hasMore:
	""" Make the API call """ 
	print (">>> API call")
	aResult = requests.post(aURL, headers=aHeaders, data=aData)
	print ("<<< Results")

	# If we don't get a 200 HTML response code, we didn't get a result. 
	if( aResult.status_code != 200 ):
		printmessageblock ('* Failed to get a response to call for /team/members/list')
		exit();

	# Note the JSON response
	members = aResult.json()
	totalMembers += len(members['members'])     # Keep a count of total members ( this will be verfied and unverfied accounts )

	# Iterate over the Members in the JSON
	for aMember in members['members']:
		
		# Check if there's an external ID
		if( 'external_id' in aMember['profile'] ):
			member_email = str(aMember['profile']['email'])
			team_member_id = str(aMember['profile']['team_member_id'])

			wipeExternalID(member_email, team_member_id)


	hasMore = members['has_more']                                                     # Note if there's another cursor call to make. 

	# If it's the first run, from this point onwards the API call is the /continue version.
	if ( loopCounter == 0 ):
		aURL = 'https://api.dropboxapi.com/2/team/members/list/continue'
		aData = json.dumps({'cursor': members['cursor']}) 


"""
#############################################
# Step 7
# 1. Output how long the script took to run.
#############################################
"""
totalTimeStop = datetime.datetime.fromtimestamp(time.time())
totalTimeInSeconds = (totalTimeStop-totalTimeStart).total_seconds()
timeAsStr = getTimeInHoursMinutesSeconds( totalTimeInSeconds )
printmessageblock( " Script finished running, it took                                           %s." % ( timeAsStr ) )

print ( "\nStopping: %s" % getPrettyTime() )


