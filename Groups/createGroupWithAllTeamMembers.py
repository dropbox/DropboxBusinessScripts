#!/usr/bin/python
# -*- coding: latin-1 -*-

import json
import requests
import os                             # Allows for the clearing of the Terminal Window
import csv                            # Allows outputting to CSV file


"""
A Script to create a group called 'GRP_ALL_TEAM_MEMBERS', and iterate over all members of a team, adding all member to the group.

Note: 
  This example assumes small number of users in team. If you had a large number of members you might want to make multiple calls
  with batches of users and a delay built in to allow time to process the request. 


Requirements:
  Script writen testing on Python 3.6.5

  Dropbox API Token needed inserted just below this comments section.
  The following scoped permissions needed:
  * team_data.member 
  * members.read
  * groups.write

Pre-requisites:
* Scripts requires library 'Requests' - You can install using "pip install requests"

"""

"""
Set your OAuth Tokens here
"""
gScopedToken =  ''     # API Scoped Token    

gGroupName = 'GRP_ALL_TEAM_MEMBERS'




"""
DO NOT EDIT BELOW THIS POINT
"""



"""
# ############################################
# Step 0
# Clear the terminal window, not essential but makes it easier to read this way.
# ############################################
"""

os.system('cls' if os.name=='nt' else 'clear')


"""
# ############################################
# Step 1
# 1. Check if we have the necessary Tokens.
# 2. If not, ask the user to enter it.
# ############################################
"""
if (gScopedToken == ''):
  gScopedToken = raw_input('Enter your Dropbox Business API App token: ')

aHeaders = {'Content-Type': 'application/json', 
    'Authorization': 'Bearer %s' % gScopedToken}

"""
#############################################
# Step 1
# 1. Setup the necessary variables to get list of members. 
#############################################
"""
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
dbxMembers = []

print ("> Retrieving Dropbox Users via API")

while hasMore:

  print (">>> API call")
  """ Make the API call """ 
  aResult = requests.post(aURL, headers=aHeaders, data=aData)

  print ("<<< Results")

  # If we don't get a 200 HTML response code, we didn't get a result. 
  if( aResult.status_code != 200 ):
    print ('>>> Failed to get a response to call for /team/members/list')
    print (aResult.text)
    exit();

  # Note the JSON response
  members = aResult.json()

  # Iterate over the Members in the JSON
  for aMember in members['members']:
    dbxUsers.append( aMember )
    memDetails = {"user": {".tag":"team_member_id", "team_member_id": aMember['profile']['team_member_id']},"access_type": "member"}
    dbxMembers.append( memDetails )
    
  hasMore = members['has_more']            # Note if there's another cursor call to make. 

  # If it's the first run, from this point onwards the API call is the /continue version.
  if ( loopCounter >= 0 ):
    aURL = 'https://api.dropboxapi.com/2/team/members/list/continue'
    aData = json.dumps({'cursor': members['cursor']}) 
    loopCounter += 1

print (" We have " + str(len(dbxUsers)) + " Dropbox Team members in memory") 



"""
#############################################
# Step 3
# 1. Create a Group based on variable gGroupName
#############################################
"""

aURL = 'https://api.dropboxapi.com/2/team/groups/create'
aData = json.dumps({'group_name': gGroupName, 'group_management_type': 'company_managed'}) 


aResult = requests.post(aURL, headers=aHeaders, data=aData)

# If we don't get a 200 HTML response code, we didn't get a result. 
if( aResult.status_code != 200 ):
  print ('>>> Failed to create a group using /2/team/groups/create')
  print (aResult.text)
  exit();

# Note the JSON response
group = aResult.json()

# Note the Group ID
aGroupID = group['group_id']


"""
#############################################
# Step 3
# 1. Create a Group based on variable gGroupName
#############################################
"""

aURL = 'https://api.dropboxapi.com/2/team/groups/members/add'
aData = json.dumps({"group": {".tag": "group_id", "group_id": aGroupID}, "members": dbxMembers, "return_members": False}) 


aResult = requests.post(aURL, headers=aHeaders, data=aData)

# If we don't get a 200 HTML response code, we didn't get a result. 
if( aResult.status_code != 200 ):
  print ('>>> Failed to add members to group using /2/team/groups/members/add')
  print (aResult.text)
  exit();


print ( 'All members added to Group')
print ('\n\n\nExiting Script.')
