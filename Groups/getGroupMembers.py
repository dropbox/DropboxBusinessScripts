#!/usr/bin/python
# -*- coding: latin-1 -*-

import json
import requests
import pprint                         # Allows Pretty Print of JSON
import os                             # Allows for the clearing of the Terminal Window
import csv                            # Allows outputting to CSV file
import time, datetime
import sys


"""
Example script to pull out a report on Groups and their members. 
Script is limited to report on 1000 groups and 1000 members per group.

It will generate two files:
- groups.csv
- member-groups.csv

groups.csv: List of groups, management type, member count, and all member emails list thereafter
member-groups.csv: email address of member and group name. 


Requirements:
  Script tested on Python 3.6.5

  One Dropbox API Token is needed, inserted just below this comments section.
  * Team Information

Pre-requisites:
* Scripts requires library 'Requests' - You can install using "pip install requests"

"""





"""
Set your OAuth Tokens here
"""
gTokenTI = ''     # Team Information App Token








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

#############################################
# Function to return a list of members for a group
#############################################
def getGroupMembers ( group_id ):
	members_list = []

	aHeaders = {'Content-Type': 'application/json', 
		'Authorization': 'Bearer %s' % gTokenTI}
	aURL = 'https://api.dropboxapi.com/2/team/groups/members/list'
	aData = json.dumps({'group':{'.tag':'group_id','group_id': group_id},'limit': 1000})

	print (">>> API call to get Group Members")

	""" Make the API call """ 
	aResult = requests.post(aURL, headers=aHeaders, data=aData)

	print ("<<< Results")

	# If we don't get a 200 HTML response code, we didn't get a result. 
	if( aResult.status_code != 200 ):
		print ('>>> Failed to get a response to call for /2/team/groups/members/list ')
		print (aResult.text)
		exit();

	# Note the JSON response
	group_members = aResult.json()

	for member in group_members['members']:
		members_list.append( member['profile']['email'])

	return members_list




"""
#############################################
# Step 1
# 1. Load groups, iterate over them
#############################################
"""

aHeaders = {'Content-Type': 'application/json', 
		'Authorization': 'Bearer %s' % gTokenTI}
aURL = 'https://api.dropboxapi.com/2/team/groups/list'
aData = json.dumps({'limit': 1000}) 

print (">>> API call to get Groups")

""" Make the API call """ 
aResult = requests.post(aURL, headers=aHeaders, data=aData)

print ("<<< Results")

# If we don't get a 200 HTML response code, we didn't get a result. 
if( aResult.status_code != 200 ):
	print ('>>> Failed to get a response to call for /2/team/groups/list ')
	print (aResult.text)
	exit();

# Note the JSON response
teamGroups = aResult.json()

with open( 'groups.csv', 'wt') as csvfile:
	# Define the delimiter
	writer = csv.writer(csvfile, delimiter=',')
	writer.writerow(['group name','management type', 'members count', 'members'])


	with open( 'member-groups.csv', 'wt') as csvmemberfile:
		# Define the delimiter
		memberwriter = csv.writer(csvmemberfile, delimiter=',')
		memberwriter.writerow(['member','group name'])


		for group in teamGroups['groups']:

			group_id = group['group_id']
			group_name = group['group_name']
			management_type = group['group_management_type']['.tag']
			member_cnt = group['member_count']
			members = ['']

			if ( member_cnt > 0 ):
				members = getGroupMembers( group_id )

				for member in members:
					memberwriter.writerow([member,group_name])

			myList = [group_name, management_type, str(member_cnt)]
			myList.extend( members )

			writer.writerow(myList)


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
