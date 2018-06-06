#!#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import requests
import os                             # Allows for the clearing of the Terminal Window
import csv                            # Allows outputting to CSV file
import time, datetime
import mammoth						  # Used to convert Word to Markdown
import glob

"""
********************************************************************************************************************

The intention of this script is to:
* Iterate over a list of users email addresses and for every user look for a folder matching that email address in the 
  same folder as this running script. 
  For each .docx file in the folder, convert to HTML and create a Paper document matching that in the users Dropbox Account.

  If email address in the file 'users.csv' isn't a valid Team Members email address we skip it. 

Script expects:
  * a file of users called users.csv, in same folder as this script, which is a CSV list of email addresses, one email *lowercase* per row.
  * a folder called 'Paper Docs', in same folder as this script
  * for every user listed in CSV that there will be a folder name matching that email address ( again lowercase ) inside
    the folder 'WordDocs'.
    If it can't find a folder it moves onto next user in list. 
  * the files per user to be .docx Word Documents


Prerequisites:
* Python 3.6+
* Requests library installed 'pip install requests' 
* Mammoth library installed  'pip install mammoth'      [https://github.com/mwilliamson/python-mammoth]


********************************************************************************************************************
"""

gTokenTMM = ''     # Team Member Management token for TARGET team
gTokenTMFA = ''    # Team Member File Access

gUsersList = 'users.csv'



"""
********************************************************************************************************************
                                             DO NOT EDIT BELOW THIS POINT
********************************************************************************************************************
"""

#############################################
# Function to return a string representation of time taken
#############################################
def getTimeInHoursMinutesSeconds( sec ):

    return time.strftime("%H hrs %M mins %S sec", time.gmtime(sec))

#############################################
# Function to print Message to console in a tidy box
#############################################
def printmessageblock( str ):
  print ("\n*********************************************************")
  print ("* %s" % (str))
  print ("*********************************************************\n")
  return;

#############################################
# Function to return create a Paper document in a user Account
#############################################
def uploadPaperDoc( team_member_id, tmfa_token, markupData ):

	# Get current directory
	#cwd = os.getcwd()
	#bytes_read = open(markupFile, "rb").read()


	lArguments = json.dumps({'import_format': 'html'})
	
	lHeadersTMFA = {'Content-Type': 'application/octet-stream',
		'Authorization': 'Bearer %s' % tmfa_token, 
		'Dropbox-API-Select-User': '%s' % team_member_id,
		'Dropbox-API-Arg': '%s' % lArguments}


	lURL = "https://api.dropboxapi.com/2/paper/docs/create"

	aResult = requests.post(lURL, headers=lHeadersTMFA, data = markupData)  # Create Paper Doc

	if( aResult.status_code != 200 ):
		printmessageblock ('* Failed to get a response to call for /paper/docs/create. \nWe got an error [%s] with text "%s"' % (aResult.status_code, aResult.text))
	
	return;





# Track how long script takes to run
totalTimeStart = datetime.datetime.fromtimestamp(time.time())

# Global Variables
gUsers = []

#############################################
# Step 0
# Clear the terminal window, not essential but makes it easier to read this way.
#############################################

os.system('cls' if os.name=='nt' else 'clear')




#############################################
# Step 1
# Check that there's Tokens provided. 
#############################################
if ( len(gTokenTMM) <= 0 or len(gTokenTMFA) <= 0 ):
	printmessageblock ( "It would appear you're missing one of the necessary API Tokens. Ending script." )
	exit()




#############################################
# Step 2
# Get the list of users to analyze
#############################################

# Check we have a users file
bHaveCSV = os.path.isfile( gUsersList ) 

if (not bHaveCSV):
	print('We could not find a file listing users to insert Paper Documents for. ')
	exit();


# Open file of users to upload files for
with open( gUsersList, 'rt') as csvfileRead:
	# Open file to read from
	reader = csv.reader(csvfileRead)

	#Iterate through each row of the CSV.
	for row in reader:
		gUsers.append( row[0].lower() ) # Lower case so we can compare to Dropbox ( always lowercase )

	if ( len(gUsers) <= 0 ):

		# Check that we have users
		print("We could not any users in file '%s' to work on. " % gUsersList)
		exit();


#############################################
# Step 3
# Get a list of all Team Members
# Only note the users we've been told to work on in inout users file
#############################################

aHeaders = {'Content-Type': 'application/json', 
		'Authorization': 'Bearer %s' % gTokenTMM}
aURL = 'https://api.dropboxapi.com/2/team/members/list'
aData = json.dumps({'limit': 300}) 

hasMore = True;      # Controls how long we stay in while loop loading users. 
loopCounter = 0      # Count of how many times we hit the API 
dbxUsers = []        # List of Dropbox Users
aTotalMembers = 0

print ("> Retrieving Dropbox Users via API")
timestart = datetime.datetime.fromtimestamp(time.time())			# Used to note start and calculate total time script took to run.

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

		aTotalMembers += 1. # Count number of team members

		#Check if this member is one we've been asked to work on.
		if (aMember['profile']['email'] in gUsers):
			dbxUsers.append( aMember )

	hasMore = members['has_more']            # Note if there's another cursor call to make. 

	# If it's the first run, from this point onwards the API call is the /continue version.
	if ( loopCounter >= 0 ):
		aURL = 'https://api.dropboxapi.com/2/team/members/list/continue'
		aData = json.dumps({'cursor': members['cursor']}) 
		loopCounter += 1


# How long did the APIs take?
timestop = datetime.datetime.fromtimestamp(time.time())
print ((" We have %s Dropbox Team members in memory from %s API Calls. it took %s seconds.\n\n") % (str(len(dbxUsers)),str(loopCounter),str((timestop-timestart).total_seconds())) )

print( "\n\nThere are " + str(aTotalMembers) + " members on the team" );
print ( "We're to create Paper documents for " + str(len(dbxUsers)) + " users." )





#############################################
# Step 4
# Iterate over each team member, look for a folder name matching that users
# email address.
# Iterate over every .docx file, convert to markdown and upload to users account!
#############################################

for aCurrentUser in dbxUsers:

	# Locate a folder matching email address of this user
	# Check we have a folder
	thisPath = 'WordDocs/' + aCurrentUser['profile']['email']
	bHaveCSV = os.path.isdir( thisPath ) 

	if ( not bHaveCSV ):
		print ('\n--No source folder found for user ' + aCurrentUser['profile']['email'])
		continue;

	# Iterate over each file in Folder
	# First get list of .docx files
	docsToConvert = glob.glob( thisPath + '/*.docx' )

	for aDoc in docsToConvert:
		print (aDoc)
		md = mammoth.convert_to_html( aDoc )
		
		uploadPaperDoc( aCurrentUser['profile']['team_member_id'], gTokenTMFA, md.value )


			


#############################################
# Final step
# 1. Output how long the script took to run.
#############################################

totalTimeStop = datetime.datetime.fromtimestamp(time.time())
totalTimeInSeconds = (totalTimeStop-totalTimeStart).total_seconds()
timeAsStr = getTimeInHoursMinutesSeconds( totalTimeInSeconds )
printmessageblock( " Script finished running, it took                                           %s." % ( timeAsStr ) )


print( "Script finished")
