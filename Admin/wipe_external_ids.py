#!/usr/bin/python
# -*- coding: latin-1 -*-

import json
import requests
import os                             # Allows for the clearing of the Terminal Window
import csv                            # Allows outputting to CSV file
import time, datetime
import sys
import pprint

"""
The intention of this script is to:

- Load a CSV list (config.csv) of users to wipe External IDs for
- Iterate over all members of a team
- If team member email is in the CSV list, we'll attempt to set its External ID to ""

Requirements:
  Script writen and tested on Python 3.6.5

  Dropbox API Token needs to be inserted just below this comments section.
  It needs to have the following scoped permissions:

  - team_data.member
  - members.write


Pre-requisites:
* Scripts requires library 'Requests' - You can install using "pip install requests"

"""

"""
Set your OAuth Tokens here
"""
gTokenTMM = ''    	# Insert SCOPED API token here

# Source File Here
gListOfMembersToWorkOn = 'config.csv'

# Flag to control actually permanently wipe of 'external_id'
gRunInTestMode = False




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
	aData = json.dumps({"user": { ".tag": "team_member_id", "team_member_id": team_member_id}, "new_external_id": ""})
	lHeadersTMFA = {'Content-Type': 'application/json',
		'Authorization': 'Bearer %s' % gTokenTMM} 

	aResult = None

	if (not gRunInTestMode):
		aResult = requests.post(aURL, headers=lHeadersTMFA, data=aData)  # Wipe 'external_id'
		print ( "Wiped External ID for %s | %s" % (email,team_member_id) )
	else:
		print ( "Testing call to wipe External ID for %s | %s" % (email,team_member_id) )
		return True

	if( aResult.status_code != 200 ):
		print ( "ERROR: Failed to wipe External ID for email: %s, error code %s, '%s'" % (email, aResult.status_code, aResult.text))
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


"""
# ############################################
# Step 1 
# Get a list of users to wipe 'external_id' on.
# If empty or not found script will stop running.
# ############################################
"""

gUsersToChange = {}
bAnalyzeAll = False

# Check we have a config file
bHaveCSV = os.path.isfile( gListOfMembersToWorkOn ) 

if (not bHaveCSV):
	printmessageblock('We could not find config file listing users to work on. Ending script! ')
	print ( "Stopping: %s" % getPrettyTime() )
	exit();

# Open file of users to analyze
with open( gListOfMembersToWorkOn, 'r') as csvfileRead:
	# Open file to read from
	reader = csv.reader(csvfileRead)

	#Iterate through each row of the CSV.
	for row in reader:
		gUsersToChange[row[0].lower()] = row[0].lower()  # Lower case so we can compare to Dropbox ( always lowercase )

	if ( len(gUsersToChange) <= 0 ):

		# Check that we have users
		printmessageblock("We could not find any users in config file '%s' to work on. Ending script." % aListOfMembersToReportOn)
		print ( "Stopping: %s" % getPrettyTime() )
		exit();


"""
# ############################################
# Step 1 
# Get a list of all team members to locate the ones we've to change
# ############################################
"""
aHeaders = {'Content-Type': 'application/json', 'Authorization': 'Bearer %s' % gTokenTMM}
aURL = 'https://api.dropboxapi.com/2/team/members/list'
aData = json.dumps({'limit': 100, 'include_removed': True}) 

hasMore = True;
loopCounter = 0;
totalMembers = 0
members_wiped = 0

while hasMore:
	""" Make the API call """ 
	print (">>> API call")
	aResult = requests.post(aURL, headers=aHeaders, data=aData)
	print ("<<< Results")

	# If we don't get a 200 HTML response code, we didn't get a result. 
	if( aResult.status_code != 200 ):
		printmessageblock ('* Failed to get a response to call for /team/members/list')
		print (aResult.text)
		exit();

	# Note the JSON response
	members = aResult.json()
	totalMembers += len(members['members'])     # Keep a count of total members ( this will be verfied and unverfied accounts )

	# Iterate over the Members in the JSON
	for aMember in members['members']:
		
		memberEmail = aMember['profile']['email'].strip()
		team_member_id = aMember['profile']['team_member_id'].strip()

		# If this member is in our CSV list of members to change
		if ( memberEmail in gUsersToChange ):
			wipeExternalID(memberEmail, team_member_id)
			members_wiped = members_wiped + 1


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

print ( "\n\nIterated over members: " + str(totalMembers))
print ( "Wiped external ID for: " + str(members_wiped) + "\n\n")

totalTimeStop = datetime.datetime.fromtimestamp(time.time())
totalTimeInSeconds = (totalTimeStop-totalTimeStart).total_seconds()
timeAsStr = getTimeInHoursMinutesSeconds( totalTimeInSeconds )
printmessageblock( " Script finished running, it took %s seconds." % ( timeAsStr ) )

print ( "\nStopping: %s" % getPrettyTime() )


