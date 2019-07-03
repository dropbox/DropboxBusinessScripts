import json
import requests
import os                             # Allows for the clearing of the Terminal Window
import csv                            # Allows outputting to CSV file
import time, datetime 

"""
********************************************************************************************************************

The intention of this script is to:

Pull out and generate a CSV listing of all the members of your Dropbox Team.
The script requires you to set the variable aTokenTMM equal to your Team Member Management OAuth token.

The outputted CSV will have the 
'First name',
'Last name',
'Email address', 
'Account status', 
'Role', 
'Team member ID', 
'External ID', 
'Email verified', 
'Joined on'

Requirements:
  Script tested on Python 3.6.5

  One Dropbox API Token is needed, inserted just below this comments section.
  * Team Member Management

Pre-requisites:
* Scripts requires library 'Requests' - You can install using "pip install requests"

********************************************************************************************************************
"""



"""
Set your OAuth Token here with 'Team Member Management' permissions
"""

aTokenTMM = '' # Team Member Management 

"""
********************************************************************************************************************
                                             DO NOT EDIT BELOW THIS POINT
********************************************************************************************************************
"""

#############################################
# Function to return current Timestamp 
#############################################
def getTimeYMD():
  lRightNow = datetime.datetime.fromtimestamp(time.time()).strftime('%y%m%d-%H-%M-%S') 
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





"""
DO NOT EDIT BELOW THIS POINT
"""

totalTimeStart = datetime.datetime.fromtimestamp(time.time())


fileName = "User List.csv"							# Do not place a path 
aURL = 'https://api.dropboxapi.com/2/team/members/list'
aData = json.dumps({'limit': 200, 'include_removed': True}) 


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
# 1. Check if there 'aTokenTMM' variable is set
# 2. If not, ask the user to enter it.
#############################################
"""
if (aTokenTMM == ''):
  aTokenTMM = raw_input('Enter your Dropbox Business API App token (Team Member Management permission): ')

aHeaders = {'Content-Type': 'application/json', 'Authorization': 'Bearer %s' % aTokenTMM}




"""
#############################################
# Step 2
# 1. Open a CSV File
# 2. Iterate over the list and populate the file
#############################################
"""

fileName = ("%s " + fileName) % getTimeYMD()
hasMore = True;
loopCounter = 0;
totalMembers = 0

with open( fileName, 'w') as csvfile:
	writer = csv.writer(csvfile, delimiter=',')
	# Write the Column Headers
	writer.writerow(['First name','Last name','Email address', 'Account status', 'Role', 'Team member ID', 'External ID', 'Email verified', 'Joined on'])

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

			externalID = ""
			if( 'external_id' in aMember['profile'] ):
				externalID = aMember['profile']['external_id'].strip()

			joinedOnDay = ""
			if( 'joined_on' in aMember['profile'] ):
				joinedOnDay = aMember['profile']['joined_on'].strip()

			writer.writerow([aMember['profile']['name']['given_name'].strip(), 
				aMember['profile']['name']['surname'].strip(), 
				aMember['profile']['email'].strip(), 
				aMember['profile']['status']['.tag'].strip(),
				aMember['role']['.tag'].strip(),
				aMember['profile']['team_member_id'].strip(),
				externalID,
				aMember['profile']['email_verified'], 
				joinedOnDay])
						
			hasMore = members['has_more']                                                     # Note if there's another cursor call to make. 

		# If it's the first run, from this point onwards the API call is the /continue version.
		if ( loopCounter == 0 ):
			aURL = 'https://api.dropboxapi.com/2/team/members/list/continue'
			aData = json.dumps({'cursor': members['cursor']}) 

		# Increment the loop coun
	# End of while hasMore:

print ('\n\nTotal Members found: %s' % totalMembers)

"""
#############################################
# Step 5
# 1. Output how long the script took to run.
#############################################
"""
totalTimeStop = datetime.datetime.fromtimestamp(time.time())
totalTimeInSeconds = (totalTimeStop-totalTimeStart).total_seconds()
timeAsStr = getTimeInHoursMinutesSeconds( totalTimeInSeconds )
printmessageblock( " Script finished running, it took %s seconds." % ( timeAsStr ) )
