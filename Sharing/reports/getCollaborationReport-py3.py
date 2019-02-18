#!/usr/bin/python
# -*- coding: latin-1 -*-

import json
import requests
import pprint                         # Allows Pretty Print of JSON
import os                             # Allows for the clearing of the Terminal Window
import csv                            # Allows outputting to CSV file
import time, datetime

from Classes import SharedFolder      # Object to represent a single shared folder, and all it's sharing.

"""

Written using python 3.6+

BE WARNED:
* Use with discression. 
* Not testing in anger so accuracy of reporting TBC.
* Not threaded so will be slow for larger Teams / complex folder structures
 
An example script to iterate over all members of a team, for each member pull out a list of their shared folders. 
If you provide a CSV file of users emails, it will start by analyzing only those users. 
NOTE: You won't see that users full collaboration without analyzing rest of company. 
If the user is the owner of a folder... iterate over and list all the groups and users with accesss ( or invited ).
If the user is not the owner, but the owner is a member of our team, we'll ignore the folder as it'll be captured when we iterate over that users folders. 
If the user is not the owner, and the owner is not a member of our team. Note the folder details but flip it so external user is the folder owner and the user we're iterating over is the collaborator.  
Note: Assumes default of 1000 results acceptible for querying folder members     
The following output files are created. 
YY-MM-DD-paths.csv   			-> List of user and the paths to publicly shared files.
"""




"""
Set your OAuth Tokens here 
"""

aTokenTMFA = ''     # Team Member File Access
aTokenTMM =  ''    	# Team Member Management 
aTokenTI =   ''     # Team Information Access


sourceMembersToReportOn = 'config.csv'


"""
DO NOT EDIT BELOW THIS POINT
"""

fileName = 'collaboration.csv'
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
# Function to print Message to console in a tidy box
#############################################
def getTimeInHoursMinutesSeconds( sec ):

    return time.strftime("%H hrs %M mins %S sec", time.gmtime(sec))



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
# 1. Check if we have the necessary Tokens.
# 2. If not, ask the user to enter it.
#############################################
"""
if (aTokenTMFA == ''):
  aTokenTMFA = raw_input('Enter your Dropbox Business API App token (Team Member File Access permission): ')

if (aTokenTMM == ''):
  aTokenTMM = raw_input('Enter your Dropbox Business API App token (Team Member Management permission): ')

if (aTokenTI == ''):
  aTokenTI = raw_input('Enter your Dropbox Business API App token (Team Information permission): ')



"""
#############################################
# Step 2
# 1. Get the Team ID 
#############################################
"""
aHeaders = {'Authorization': 'Bearer %s' % aTokenTI}
aURL = 'https://api.dropboxapi.com/2/team/get_info'
aData = json.dumps({}) 

print (">>> API call")
""" Make the API call """ 
aResult = requests.post(aURL, headers=aHeaders, data=aData)

print ("<<< Results")

# If we don't get a 200 HTML response code, we didn't get a result. 
if( aResult.status_code != 200 ):
	print ('>>> Failed to get a response to call for /2/team/get_info')
	print (aResult.text)
	exit();

# Note the JSON response
teamInfo = aResult.json()
teamID = teamInfo['team_id'] # This tells us what Team we are, any folder not owned by this is EXTERNALLY owned.



"""
#############################################
# Step 3
# 1. Load CSV of users we want to report on
#############################################
"""
gUsersToAnalyze = []
bAnalyzeAll = False

# Check we have a Domains file
bHaveCSV = os.path.isfile( sourceMembersToReportOn ) 

if (not bHaveCSV):
	print('We could not find a file listing users to report on. ')
	print('Would you like to analyze ALL users on the team. Note this could be a very *VERY* slow process.') 
	lsAnswer = input("Type 'y' to process ALL or 'n' to cancel this script: ")

	if ( lsAnswer == 'y' or lsAnswer == 'Y'):
		bAnalyzeAll = True
	elif ( lsAnswer == 'n' or lsAnswer == 'N'): 
		print( '\nExiting script\n')
		exit()
	else:
		print("\n\nUser did not enter a 'n' or a 'y' input. Ending script.")
		exit();

if ( not bAnalyzeAll ):
	# Open file of users to analyze
	with open( sourceMembersToReportOn, 'r') as csvfileRead:
		# Open file to read from
		reader = csv.reader(csvfileRead)

		#Iterate through each row of the CSV.
		for row in reader:
			gUsersToAnalyze.append( row[0].lower() ) # Lower case so we can compare to Dropbox ( always lowercase )

		if ( len(gUsersToAnalyze) <= 0 ):

			# Check that we have users
			print("We could not any users in file '%s' to report on. " % sourceMembersToReportOn)
			print('Would you like to analyze ALL users on the team. Note this could be a very *VERY* slow process.') 
			lsAnswer = input("Type 'y' to process ALL or 'n' to cancel this script: ")

			if ( lsAnswer == 'y' or lsAnswer == 'Y'):
				bAnalyzeAll = True
			elif ( lsAnswer == 'n' or lsAnswer == 'N'):
				print( '\nExiting script\n')
				exit()
			else:
				print("\n\nUser did not enter a 'n' or a 'y' input. Ending script.")
				exit();



"""
#############################################
# Step 4
# 1. Setup the necessary variables to get list of members. 
#############################################
"""
aHeaders = {'Content-Type': 'application/json', 'Authorization': 'Bearer %s' % aTokenTMM}
aURL = 'https://api.dropboxapi.com/2/team/members/list'
aData = json.dumps({'limit': 300}) 



"""
#############################################
# Step 5
# 1. Get list of all Dropbox Team Members
# 2. Create in memory list of them.
# 3. If they match variable 'filterOut', skip them and move to skipped list.
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
print (" We have the Dropbox users in memory from " + str(loopCounter) + " API Calls. it took " + str((timestop-timestart).total_seconds()) + " seconds.")


"""
#############################################
# Step 5
# 1. Iterate over list of members
# 2. For each member:
#       Get the list of Shared Folders
#       Note the details
#############################################
"""
# Open a file to write to
newFileName = ("%s-" + fileName) % getTimeYMDHM()

with open( newFileName, 'wt') as csvfile:
	# Define the delimiter
	writer = csv.writer(csvfile, delimiter=',')
	# Write the Column Headers

	writer.writerow(['Owner email', 'Owner Name','Folder Name', 'Folder Path', 'Folder ID', 'Collaborator Email', 'Collaborator Permissions', 
		'Collaborator on Team', 'Folder Mount Status', 'Group Name', 'Group Members', 'Group Permissions', 'Group Type',
		'Team Owned Folder' ])

	#############################################
    # Iterate over the members
    ############################################
	for aMember in dbxUsers:

		# check if Analyze all is true
	    if ( not bAnalyzeAll ):
	    	
	    	# Check if aMember is in our list of 
	    	if ( aMember['profile']['email'] not in gUsersToAnalyze ):
	    		
	    		continue;

	    lHeadersTMFA = {'Content-Type': 'application/json', 
	        'Authorization': 'Bearer %s' % aTokenTMFA, 
	        'Dropbox-API-Select-User': '%s' % str(aMember['profile']['team_member_id'])} 

	    hasMore = True;
	    loopCounter = 0 
	    aMemberCSV = []

	    timestart = datetime.datetime.fromtimestamp(time.time())


        #############################################
        # Loop Through all the folders the member has
        #############################################

	    aURL = 'https://api.dropboxapi.com/2/sharing/list_folders'
	    aData = json.dumps({'limit': 300}) 

	    while hasMore:

	    	print ('\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
	    	print ('Account: %s' % aMember['profile']['email'])
	    	print ('\n+')
	    	aResult = requests.post(aURL, headers=lHeadersTMFA, data=aData)  # List_Folders
	    	print ("+++")

	    	# If we don't get a 200 HTML response code, we didn't get a result. 
	    	if( aResult.status_code != 200 ):
	     		printmessageblock ('* Failed to get a response to call for list_folders. \nWe got an error [%s] with text "%s"' % (aResult.status_code, aResult.text))
	     		next;

	    	# Note the JSON response
	    	userFolders = aResult.json()

	        # Note: Unmounted Shared Folders can be identified by the absense of 'path_lower'

	    	###########################################
	    	# Iterate over the users folders 
	    	###########################################
	    	for userFolder in userFolders['entries']:
	    		# Reset the variable to note the file details
	    		aMemberCSVBody = []

	    		mySharedFolder = SharedFolder()
	    		mySharedFolder.team_member_id = aMember['profile']['team_member_id'] 
	    		mySharedFolder.team_member_name = aMember['profile']['name']['display_name']
	    		mySharedFolder.team_member_email = aMember['profile']['email']
	    		mySharedFolder.email_is_verified = aMember['profile']['email_verified']
	    		mySharedFolder.account_status = aMember['profile']['status']['.tag']

	    		try:
	    			path_lower = userFolder['path_lower']
	    		except KeyError:
	    			path_lower = None

	    		mySharedFolder.is_team_folder = True if (userFolder['is_team_folder'] == 'true' ) else False
	    		mySharedFolder.path_lower = path_lower
	    		mySharedFolder.share_folder_id = userFolder['shared_folder_id']   # Preview URL
	    		mySharedFolder.folder_name = userFolder['name']                   # Folder Name

	    		if ( path_lower == None ):
	    			mySharedFolder.mount_status = 'UNMOUNTED' # It's an UNMOUNTED folder if path_lower is empty
	    		else:
	    			mySharedFolder.mount_status = 'MOUNTED' # It's an UNMOUNTED folder if path_lower is empty

	    		mySharedFolder.preview_url = userFolder['preview_url'] # Preview URL
	    		mySharedFolder.folder_permission = userFolder['access_type']['.tag']                                         ### So we know if user owns the folder!!!


	    		#############################################
	    		# Loop through all the members of the folder
	    		#############################################
	    		#pprint.pprint( userFolder )
	    		aSubURL = 'https://api.dropboxapi.com/2/sharing/list_folder_members'
	    		aSubData = json.dumps({'shared_folder_id': userFolder['shared_folder_id'], 'actions': [], 'limit': 1000}) 
	    		#pprint.pprint( aSubData )

	    		aResult = requests.post(aSubURL, headers=lHeadersTMFA, data=aSubData)
	    		# If we don't get a 200 HTML response code, we didn't get a result. 
	    		if( aResult.status_code != 200 ):
	    			printmessageblock ('* Failed to get a response to call for list_folder_members. \nWe got an error [%s] with text "%s"' % (aResult.status_code, aResult.text))
	    			continue;

	    		# Note the JSON response
	    		userFolderMembers = aResult.json()

	    		#########################################
	    		#
	    		# Decision time. 
	    		# We only want to record to file details from a folder owners point of view. 
	    		# If this user is NOT the folder owner, we need to work out who is because if it's owned by an external party we do need 
	    		# to record the fact that THIS user is a member of an externally owned/shared folder. 
	    		#
	    		# So, if folder is owned by a team member, don't write anything to file and move on to next folder ( we'll catch that later )
	    		#
	    		# However if folder owned by external resource then we print ONE line showing who the external owner is, and this user as contrib.
	    		#
	    		#########################################


	    		printRowAnyways = True # If no groups / invitees / users

	    		print ( 'Folder: %s' % mySharedFolder.folder_name)
	    		groupcnt = 0
	    		inviteescnt = 0
	    		usercnt = 0

	    		##########################################
	    		# Loop over all the Groups of the folder
	    		##########################################
	    		if len(userFolderMembers['groups'] ) > 0 :
	    			groupcnt = len(userFolderMembers['groups'] )

	    			printRowAnyways = False
	    			for userGroups in userFolderMembers['groups']:
		    			
		    			mySharedFolder.addGroup( userGroups['group']['group_name'], 
		    				userGroups['group']['member_count'],
		    				userGroups['access_type']['.tag'],
		    				userGroups['group']['group_type']['.tag'])

		    	# Invitees
		    	inviteescnt = len(userFolderMembers['invitees'] )
		    	#if len(userFolderMembers['invitees'] ) > 0 :
		    		# TO FIGURE OUT

		    	##########################################
	    		# Loop over all the Users of the folder
	    		##########################################
		    	if len(userFolderMembers['users'] ) > 0 :
		    		usercnt = len(userFolderMembers['users'] )
    				printRowAnyways = False
    				for folderUser in userFolderMembers['users']:

    					userEmailAddress = ''
    					userName = mySharedFolder.team_member_name

    					# Check for email address 
    					if (folderUser['user']['same_team'] == True):
    						userEmailAddress = dbxEmailLookup.get( folderUser['user']['team_member_id'] )   # Get team members email address
    					else:
    						# We have to do an API call on the Account ID to get the name
    						aUserAccURL = 'https://api.dropboxapi.com/2/users/get_account'
    						aUserAccData = json.dumps({'account_id': folderUser['user']['account_id']})

    						aResult = requests.post(aUserAccURL, headers=lHeadersTMFA, data=aUserAccData)

    						# If we don't get a 200 HTML response code, we didn't get a result. 
    						if( aResult.status_code != 200 ):
    							printmessageblock ('* Failed to get user account. \nWe got an error [%s] with text "%s"' % (aResult.status_code, aResult.text))
    							userEmailAddress = folderUser['user']['same_team']   # Account ID, as we couldn't load account to get email address
    							userName = ''
    						else:
    							# Note the JSON response
    							userAccount = aResult.json()
    							userEmailAddress = userAccount['email']  # Email address of the account
    							userName = userAccount['name']['display_name']
    					
    					mySharedFolder.addUser( folderUser['access_type']['.tag'],
    						folderUser['is_inherited'],
    						userEmailAddress,
    						folderUser['user']['same_team'], 
    						userName)
    			print ( '    Groups: %d  |  Invitees: %d  |  Users: %d' % (groupcnt, inviteescnt, usercnt))

    			##########################################
	    		# We should now have a folder object with list of
	    		# Groups / Invitees / Users.
	    		# Decision time!!!
	    		# 
	    		##########################################

	    		if ( mySharedFolder.isOwnedByUser() ):
	    			#pprint.pprint( 'Folder owned by User')
	    			rows = mySharedFolder.getOwnerOwnedFolderRows()
	    			for row in rows:
	    				#pprint.pprint ( row )
	    				writer.writerow( row )
	    		elif ( mySharedFolder.isOwnedByTeamMember() ):
	    			print("    This folder is owned by another team member. This will be reflected when we parse their owned folders. ")
	    		else:
	    			writer.writerow ( mySharedFolder.getExternallyOwnedFolderRow() )


	    	try:
	    	    myCursor = userFolder['cursor']
	    	    aData = json.dumps({'cursor': myCursor}) 
	    	except KeyError:
	    	    hasMore = False

	    	# How long did this one account take?
	    	accTimestop = datetime.datetime.fromtimestamp(time.time())

	    	accTime = (accTimestop-timestart).total_seconds()
	    	soFar = (accTimestop-totalTimeStart).total_seconds()

	    	print ('\nTime for account listing:                                                                              %s' % (getTimeInHoursMinutesSeconds(accTime)))
	    	print ('Total so far:                                                                                                                 %s' % (getTimeInHoursMinutesSeconds(soFar)))
	    	print ('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')



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


