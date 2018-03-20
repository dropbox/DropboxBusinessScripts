#!/usr/bin/python
# -*- coding: latin-1 -*-

import json
import requests
import pprint                         # Allows Pretty Print of JSON
import os                             # Allows for the clearing of the Terminal Window
import csv                            # Allows outputting to CSV file
import time, datetime 

"""
A Script to iterate over all members of a team and extract the data they're using.

An output file will be created using this naming convention 

YY-MM-DD-AccountsDataSummary.csv   			

It will contain columns:
email, account status, space used (bytes), space used, space allocated (bytes), space allocated


NOTE:
If Member Space Allocation is NOT USED, or if users are part of a exception list:
  - They users will show a Zero for columns 'space allocated (bytes)' and 'space allocated' 
  - They are part of the Teams overall space allowance

"""

"""
Set your OAuth Token here with 'Team Member Management' permissions
"""
aTokenTMM = ''    	# Team Member Management
aTokenTMFA = ''     # Team Member File Access


"""
DO NOT EDIT BELOW THIS POINT
"""

fileName = 'AccountsDataSummary.csv'

totalTimeStart = datetime.datetime.fromtimestamp(time.time())

userSharedLinks =[]				# List of users and their shared links.
failedToListLinks = []			# List of users we failed to list links for.


#############################################
# Function to return a string representation of bytes
#############################################
def getBytesAsGB_MB_KB( num ):

  # variables to convert form bytes to other format.
  terabyte = 1099511627776
  gigabyte = 1073741824
  megabyte = 1048576
  kilobyte = 1024

  kb = 0
  mb = 0
  gb = 0
  tb = 0

  if ( type(num) is str ):
    if ( '.' in num ):
      num = int(float(num))
    else:
      num = int( num )

  # Copy of the NUM we'll reduce as we progress
  numRemains = num

  # Check for GB
  if (numRemains > terabyte):
    tb = numRemains / terabyte
    numRemains = numRemains - ( tb * terabyte )

  if (numRemains > gigabyte):
    gb = numRemains / gigabyte
    numRemains = numRemains - ( gb * gigabyte )
  
  if (numRemains > megabyte ):
    mb = numRemains / megabyte
    numRemains = numRemains - ( mb * megabyte )

  if (numRemains > kilobyte ):
    kb = numRemains / kilobyte
    numRemains = numRemains - ( kb * kilobyte )
  else:
    kb = numRemains
  
  return ('%s TB, %s GB, %s MB, %s KB' % (tb, gb,mb,kb))

#############################################
# Function to return current Timestamp 
#############################################
def getTimeYMDHM():
  lRightNow = datetime.datetime.fromtimestamp(time.time()).strftime('%y%m%d-%H-%M') 
  return lRightNow;


#############################################
# Function to print Message to console in a tidy box
#############################################
def printmessageblock( str ):
  print "\n*********************************************************"
  print "* %s" % (str)
  print "*********************************************************\n"
  return;

#############################################
# Function to return a Token which used a 
# Team Member File Access token & Member ID  
#############################################
def getTokenWithTeamMemberFileAccess( aTokenTMFA, member_id ):
  lHeadersTMFA = {'Content-Type': 'application/json', 
                'Authorization': 'Bearer %s' % aTokenTMFA, 
                'Dropbox-API-Select-User': '%s' % str(member_id)}   
  return lHeadersTMFA;


#############################################
# Function to get list of Team Members paths 
#############################################
def getTeamMembersSpaceUsage( aMember ):
  aURL = 'https://api.dropboxapi.com/2/users/get_space_usage'
  aData = json.dumps(None) 

  timestart = datetime.datetime.fromtimestamp(time.time())

  lHeaders = getTokenWithTeamMemberFileAccess( aTokenTMFA, aMember[1][0] )


  print ("\n+ %s" % aMember[0])
  aResult = requests.post(aURL, headers=lHeaders, data=aData)
  print ("+++")

  # If we don't get a 200 HTML response code, we didn't get a result. 
  if( aResult.status_code != 200 ):
    printmessageblock ('* Failed to get a response to call for get_space_usage. \nWe got an error [%s] with text "%s"' % (aResult.status_code, aResult.text))
    return [];

  # Note the JSON response
  spaceUsage = aResult.json()

  used = spaceUsage['used']
  allocated = spaceUsage['allocation']['user_within_team_space_allocated']

  timestop = datetime.datetime.fromtimestamp(time.time())
  print ( '/get_space_usage Time taken: %s seconds' % (timestop-timestart).total_seconds())

  return [used,allocated];

"""
#############################################
# Step 0
# Clear the terminal window, not essential but makes it easier to read this way.
#############################################
"""

os.system('cls' if os.name=='nt' else 'clear')



"""
#############################################
# Step 1
# 1. Check if there 'aToken' variable is set
# 2. If not, ask the user to enter it.
#############################################
"""
if (aTokenTMFA == ''):
  aTokenTMFA = raw_input('Enter your Dropbox Business API App token (Team Member File Access permission): ')


if (aTokenTMM == ''):
  aTokenTMM = raw_input('Enter your Dropbox Business API App token (Team Member Management permission): ')

aHeaders = {'Content-Type': 'application/json', 'Authorization': 'Bearer %s' % aTokenTMM}



"""
#############################################
# Step 2
# 1. Get list of all Dropbox Team Members
# 2. Create in memory list of them.
#############################################
"""
hasMore = True;
loopCounter = 0 
dbxUsers = []

aURL = 'https://api.dropboxapi.com/2/team/members/list'
aData = json.dumps({'limit': 300}) 

print ("> Retrieving Dropbox Users via API")
timestart = datetime.datetime.fromtimestamp(time.time())

while hasMore:

	print (".")
	""" Make the API call """ 
	aResult = requests.post(aURL, headers=aHeaders, data=aData)

	print ("...")

	# If we don't get a 200 HTML response code, we didn't get a result. 
	if( aResult.status_code != 200 ):
		print ('>>> Failed to get a response to call for /team/members/list')
		print (aResult.text)
		exit();

	# Note the JSON response
	members = aResult.json()

	# Iterate over the Members in the JSON
	for aMember in members['members']:
		#pprint.pprint( aMember )
		dbxUsers.append( [aMember['profile']['email'], [aMember['profile']['team_member_id'], aMember['profile']['status']['.tag']] ] )

	hasMore = members['has_more']            # Note if there's another cursor call to make. 

	# If it's the first run, from this point onwards the API call is the /continue version.
	if ( loopCounter >= 0 ):
		aURL = 'https://api.dropboxapi.com/2/team/members/list/continue'
		aData = json.dumps({'cursor': members['cursor']}) 
		loopCounter += 1

timestop = datetime.datetime.fromtimestamp(time.time())
print (" We have the Dropbox users in memory from %s API Calls. it took %s seconds.") % (loopCounter,(timestop-timestart).total_seconds())



"""
#############################################
# Step 3
# 1. Iterate over all Members of the Team, make a call to get their space usage, and write to file.
#############################################
"""

# Open a file to write to
newFileName = ("%s-" + fileName) % getTimeYMDHM()

with open( newFileName, 'wt') as csvfile:
  # Define the delimiter
  writer = csv.writer(csvfile, delimiter=',')
  # Write the Column Headers
  writer.writerow(['email','account status','space used (bytes)','space used', 'space allocated (bytes)', 'space allocated'])

  # Iterate over the members
  for aMember in dbxUsers:

  #  if ( aMember[0] == 'jeremy@hanfordinc.com'):
      result = getTeamMembersSpaceUsage( aMember )

      new_item = [aMember[0], aMember[1][1], result[0], getBytesAsGB_MB_KB(result[0]), result[1], getBytesAsGB_MB_KB(result[1])]
      #pprint.pprint(new_item)
      writer.writerow(new_item)






"""
#############################################
# Step 4
# 1. Output how long the script took to run.
#############################################
"""
totalTimeStop = datetime.datetime.fromtimestamp(time.time())
printmessageblock( " Script finished running, it took %s seconds." % ((totalTimeStop-totalTimeStart).total_seconds() ) )
