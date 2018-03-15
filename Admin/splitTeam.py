import json
import requests
import pprint                         # Allows Pretty Print of JSON
import os                             # Allows for the clearing of the Terminal Window
import csv                            # Allows outputting to CSV file
import time, datetime
import sys

reload(sys)
sys.setdefaultencoding('UTF8')

"""
********************************************************************************************************************

The intention of this script is to:

Iterate through a list of users ( users.csv ), remove that member from the source team (based on the API token provided gFromTeamTOKEN) 
returning their account to being a personal individual account. 
Then immediately inviting the user to join new team (based on the API token provided gToTeamTOKEN).

Note:
  CSV file expects email, first name, last name
  One user per row

Users in target Team are invited as standard team members. They will need to ACCEPT the invitation before joining the team.
Once they accept, they will enter the invite flow, and must select option to transfer their content to company.
If you need to promote anyone to an Administrative level, do so using the Admin web pages.

Notes:
  When you remove a team member from a team:
  1. Account will be disconnected from the team and converted to an individual account
  2. Member will keep unshared files and folders, and shared folders that they own
  3. Member won't have access to team-owned folders that they were invited to after joining the team 
  4. Member will still have access to Paper docs that they own and are private

By default the script runs in MOCK or test mode. Edit the variable 'gMockRun' to make it run for real.

By default adding users to target team will send them an invite email, edit variable 'gSendWelcomeEmail' to stop this.

Script logs most console content to a file 'logfile.txt' in the location script is executed. 

** WARNING **
If you enter incorrect Target Team Token, users accounts could be orphaned as they'll be removed from Source Team but not added to
the Target Team. 

********************************************************************************************************************
"""
gFromTeamTOKEN = ''     # Team Member Management token for SOURCE team
gToTeamTOKEN = ''       # Team Member Management token for TARGET team


gMockRun = True                # If True the script emulates the actual call to the API so no account moves done
gSendWelcomeEmail = True       # If True the script will send a Welcome / invite to user added to target team.





"""
********************************************************************************************************************
                                             DO NOT EDIT BELOW THIS POINT
********************************************************************************************************************
"""


# Track how long script takes to run
totalTimeStart = datetime.datetime.fromtimestamp(time.time())

# Global Variables
gUsers = []


#############################################
# Function to return a string representation of time taken
#############################################
def getTimeInHoursMinutesSeconds( sec ):
    sec = int(sec)
    hrs = sec / 3600
    sec -= 3600*hrs

    mins = sec / 60
    sec -= 60*mins

    return '%s hrs, %s mins, %s sec' % ( hrs, mins, sec);

#############################################
# Function to print Message to console in a tidy box
#############################################
def printmessageblock( str ):
  print "\n*********************************************************"
  print "* %s" % (str)
  print "*********************************************************\n"
  return;

#############################################
# Step 0
# Clear the terminal window, not essential but makes it easier to read this way.
#############################################

os.system('cls' if os.name=='nt' else 'clear')


#############################################
# Step 1
# Check that there's a From and To Token provided. 
#############################################
if (len( gFromTeamTOKEN ) <= 0  or len( gToTeamTOKEN ) <=0 ):
	printmessageblock ( "It would appear you're missing one of the necessary API Tokens. Ending script." )
	exit()


#############################################
# Step 1
# Check if user wants to proceed. This could be distructive in removing users from Team. 
#############################################

printmessageblock('Are you sure you wish to proceed with running this script? ')
if (not gMockRun):
	print( "If you proceed, team members listed in CSV file and found in the corresponding source API team will be removed from that team.")
	print( "Script will attempt then to add them to target team")
else:
	print( "You are in MOCK RUN mode so no accounts will be removed or added.")

lsAnswer = raw_input("\nType 'y' to proceed or 'n' to cancel this script: ")

if ( lsAnswer == 'y' or lsAnswer == 'Y'):
	print( "\nExecuting script" )
elif ( lsAnswer == 'n' or lsAnswer == 'N'): 
	print( '\nExiting script\n')
	exit()
else:
	print("\n\nUser did not enter a 'n' or a 'y' input. Ending script.")
	exit();

#############################################
# Step 2
# Note the standard output to console
# Redirect standard output to File until end of script.
#############################################

print ( "Starting script, further outputs to log file." )
# Note the standard output
gstdout = sys.stdout
# Redirect standard output to log file
sys.stdout = open('logfile.txt', 'w')


#############################################
# Step 3
# Get the list of users to remove from source team
# and add to target team
#############################################
# Open a file to read from
with open( 'users.csv', 'rb') as csvfileRead:
	# Open file to read from
	reader = csv.reader(csvfileRead)
		
	gUsers = list(reader)


#############################################
# Step 4
# Iterate through each user, 
# uninvite from Source Team
#############################################

# Details for source team
aHeadersSource = {'Content-Type': 'application/json', 
		'Authorization': 'Bearer %s' % gFromTeamTOKEN}
aURLSource = 'https://api.dropboxapi.com/2/team/members/remove'

# Details for target team
aHeadersTarget = {'Content-Type': 'application/json', 
		'Authorization': 'Bearer %s' % gToTeamTOKEN}
aURLTarget = 'https://api.dropboxapi.com/2/team/members/add'


for user in gUsers:

	aEmailAddress = user[0]
	aFirstName = user[1]
	aSurname = user[2]

	# Set Users Email into parameters
	aData = json.dumps({'user': {'.tag': 'email', 'email': aEmailAddress}, 'wipe_data': False, 'keep_account': True})     

	print( "\n------------------------------------------------------------------------" )
	print( "Attempting to remove %s from source team." % aEmailAddress)

	""" Make the API call """ 
	if ( not gMockRun ):
		aResult = requests.post(aURLSource, headers=aHeadersSource, data=aData)

		#If we don't get a 200 HTML response code, we didn't get a result. 
		if( aResult.status_code != 200 ):
			print ('-- Failed to remove %s from team. %s' % (aEmailAddress, aResult.text))
			continue;
		else:
			print ('++ Successfully removed %s from team. ' % (aEmailAddress))
	else:
		print ('++ MOCK RUN: Successfully removed %s from team.' % (aEmailAddress))
		

	##########################################
	# Now try invite them to the target team!
	##########################################

	# Set Users Email into parameters
	aData = json.dumps({"new_members": [{
            "member_email": aEmailAddress,
            "member_given_name": aFirstName,
            "member_surname": aSurname,
            "send_welcome_email": gSendWelcomeEmail
        }],
        "force_async": False
        })     

	print( "\nAttempting to add %s to target team." % aEmailAddress)

	if ( not gMockRun ):
		""" Make the API call """ 
		aResult = requests.post(aURLTarget, headers=aHeadersTarget, data=aData)

		# If we don't get a 200 HTML response code, we didn't get a result. 
		if( aResult.status_code != 200 ):
			print ('-- Failed to add %s to target team. %s' % (aEmailAddress, aResult.text))
			continue;
		else:
			print ('++ Successfully added %s to target team.' % (aEmailAddress))
	else:
		print ('++ MOCK RUN: Successfully added %s to target team.' % (aEmailAddress))



#############################################
# Final step
# 1. Output how long the script took to run.
#############################################

totalTimeStop = datetime.datetime.fromtimestamp(time.time())
totalTimeInSeconds = (totalTimeStop-totalTimeStart).total_seconds()
timeAsStr = getTimeInHoursMinutesSeconds( totalTimeInSeconds )
printmessageblock( " Script finished running, it took                                           %s." % ( timeAsStr ) )

# Put standard output back to console
sys.stdout = gstdout
print( "Script finished")
