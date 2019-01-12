#!/usr/bin/python
# -*- coding: latin-1 -*-

from __future__ import print_function
import json
import requests
import os                             # Allows for the clearing of the Terminal Window
import csv                            # Allows outputting to CSV file
import time, datetime 

"""
A Script to iterate over all members of a team and extract a list of shared links 
to files and folders for each user.

Tested in Python 3.6

The following output files are created. 
* YY-MM-DD-sharedlinks.csv   			-> List of user and the paths to shared links.

Pre-requisites:
* Scripts requires library 'Requests' - You can install using "pip install requests"

"""

"""
Set your OAuth Token here with 'Team Member Management' permissions
"""
aTokenTMM = ''    	# Team Member Management
aTokenTMFA = ''     # Team Member File Access
    



"""
DO NOT EDIT BELOW THIS POINT
"""

fileName = 'sharedLinks.csv'


totalTimeStart = datetime.datetime.fromtimestamp(time.time())


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
  print ("\n*********************************************************")
  print ("* %s" % (str))
  print ("*********************************************************\n")
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
def getTeamMemberSharedLinks( aMember ):
  aURL = 'https://api.dropboxapi.com/2/sharing/list_shared_links'
  aData = json.dumps({}) 


  hasMore = True;
  loopCounter = 0 

  timestart = datetime.datetime.fromtimestamp(time.time())

  lHeaders = getTokenWithTeamMemberFileAccess( aTokenTMFA, aMember[1] )

  # List of member Shared Links
  memberSharedLinks = [] 

  while hasMore:
    print ("\n+ %s" % aMember[0])
    aResult = requests.post(aURL, headers=lHeaders, data=aData)
    print ("+++")

    # If we don't get a 200 HTML response code, we didn't get a result. 
    if( aResult.status_code != 200 ):
      printmessageblock ('* Failed to get a response to call for list_shared_links. \nWe got an error [%s] with text "%s"' % (aResult.status_code, aResult.text))
      return [];

    # Note the JSON response
    userLinks = aResult.json()

    # Iterate over the links 
    for aUserLink in userLinks['links']:
      aName = aUserLink['name']
      aLink = aUserLink['path_lower']
      expires = aUserLink.get('expires', '')

      info = [
            aMember[0],
            aUserLink['team_member_info']['display_name'], 
	    	    aUserLink['.tag'],
	    	    aName,    
	    	    aLink,    
            aUserLink['url'],
	    	    aUserLink['id'],
	    	    aUserLink['link_permissions']['resolved_visibility']['.tag'],
            expires]
      memberSharedLinks.append(info)

    hasMore = userLinks['has_more']            # Note if there's another cursor call to make. 
    if (hasMore == True):
      aData = json.dumps({'cursor': userLinks['cursor']})  

  timestop = datetime.datetime.fromtimestamp(time.time())
  print ( '/list_shared_links Time taken: %s seconds' % (timestop-timestart).total_seconds())
  return memberSharedLinks;

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
  aTokenTMFA = input('Enter your Dropbox Business API App token (Team Member File Access permission): ')


if (aTokenTMM == ''):
  aTokenTMM = input('Enter your Dropbox Business API App token (Team Member Management permission): ')

aHeaders = {'Content-Type': 'application/json', 'Authorization': 'Bearer %s' % aTokenTMM}



"""
#############################################
# Step 2
# 1. TODO
#############################################
"""
aURL = 'https://api.dropboxapi.com/2/team/members/list'
aData = json.dumps({'limit': 300}) 



"""
#############################################
# Step 3
# 1. Get list of all Dropbox Team Members
# 2. Create in memory list of them.
# 3. If they match variable 'filterOut', skip them and move to skipped list.
#############################################
"""
hasMore = True;
loopCounter = 0 
dbxUsers = []

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
		dbxUsers.append( [aMember['profile']['email'], aMember['profile']['team_member_id']] )

	hasMore = members['has_more']            # Note if there's another cursor call to make. 

	# If it's the first run, from this point onwards the API call is the /continue version.
	if ( loopCounter >= 0 ):
		aURL = 'https://api.dropboxapi.com/2/team/members/list/continue'
		aData = json.dumps({'cursor': members['cursor']}) 
		loopCounter += 1

timestop = datetime.datetime.fromtimestamp(time.time())
print (" We have the Dropbox users in memory from " + str(loopCounter) + " API Calls. it took " + str((timestop-timestart).total_seconds())+ " seconds.")



"""
#############################################
# Step 4
# 1. Reset for calls to /list_shared_links
#############################################
"""

# Open a file to write to
newFileName = ("%s-" + fileName) % getTimeYMDHM()

with open( newFileName, 'wt') as csvfile:
  # Define the delimiter
  writer = csv.writer(csvfile, delimiter=',')
  # Write the Column Headers
  writer.writerow(['email','User Name','Type','Item Name','Path','Share Link URL','Share ID','Link Permission','Expires'])

  # Iterate over the members
  for aMember in dbxUsers:

  #  if ( aMember[0] == 'jeremy@hanfordinc.com'):
      result = getTeamMemberSharedLinks( aMember )

      for item in result:
        writer.writerow(item)


    


"""
#############################################
# Step 5
# 1. Output how long the script took to run.
#############################################
"""
totalTimeStop = datetime.datetime.fromtimestamp(time.time())
printmessageblock( " Script finished running, it took %s seconds." % ((totalTimeStop-totalTimeStart).total_seconds() ) )

