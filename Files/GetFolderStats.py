#!/usr/bin/python
# -*- coding: latin-1 -*-

import json
import requests
import pprint                         # Allows Pretty Print of JSON
import os                             # Allows for the clearing of the Terminal Window
import csv                            # Allows outputting to CSV file
import time, datetime
import sys


#reload(sys)
#sys.setdefaultencoding('UTF8')

"""
A Script to iterate over all members of a team, for each member pull out a list of their folders and 
Files and give a summary of the size of data, number of files / folders. 

Note: Report shows folders the user has mounted ( added to their Dropbox account ) and does not differentiate
      between owner and collaborated on folders. 

You can optionally provide a CSV file 'config.csv' listing out on separate rows the email addresses of 
members of the team to analyze.
If you do not provide a list, or the list is empty, it will attempt to analyze ALL members.
As this could be a VERY slow process you are prompted to confirm your choice under this circumstance.      

Outputted file is 'report.csv'

It has the following column headers:
  Email Address: Team membmers email address
  Folder Path: Path of folder. Blank value is root folder. 
  Total bytes in folder and sub-folders: Total volume of bytes in this folder and all sub folders
  Total bytes - Human Readable: A human readable version of total bytes in folder and sub-folder
  Size of bytes in folder: Total of bytes for files in this folder. Excludes sub-folders and their content. 
  No. Files in folder: Number of files in this folder. Excludes sub-folders and their content. 
  No. Folders in folder: Number of folders in this folder. Excludes sub-folders and their content. 

Requirements:
  Script tested on Python 3.6.5

  Two Dropbox API Tokens needed needed inserted just below this comments section.
  * Team Member File Access
  * Team Member Management

Pre-requisites:
* Scripts requires library 'Requests' - You can install using "pip install requests"

"""

"""
Set your OAuth Tokens here
"""
aTokenTMM = ''    	# Team Member Management    
aTokenTMFA = ''     # Team Member File Access

sourceMembersToReportOn = 'config.csv'

gIncludeTeamFolders = True
gIncludeNonTeamFolders = True


"""
DO NOT EDIT BELOW THIS POINT
"""

totalTimeStart = datetime.datetime.fromtimestamp(time.time())


#############################################
# Function to return current Timestamp 
#############################################
def getTimeYMDHM():
  lRightNow = datetime.datetime.fromtimestamp(time.time()).strftime('%y%m%d-%H-%M') 
  return lRightNow;

#############################################
# Class to represent a summary of path details
#############################################
class PathSummary:
	def __init__(self):
		self.path = ''
		self.id = ''
		self.file_size_in_bytes = 0
		self.file_folder_size_in_bytes = 0
		self.num_files = 0
		self.num_folders = 0

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
# Recursive Function to take a path and analyse
# it and it's child folders
#############################################
def getSumOfPath(aPath, aPathID, aMasterFolderList, team_member_id):

	aURL = 'https://api.dropboxapi.com/2/files/list_folder'
	aData = json.dumps({'path': aPath,
		'recursive': False, 
		'include_media_info': False,
		'include_deleted': False,
		'include_has_explicit_shared_members': False,
		'include_mounted_folders': True,
		'limit': 500}) 

	lHeadersTMFA = {'Content-Type': 'application/json',
		'Authorization': 'Bearer %s' % gTokenTMFA, 
		'Dropbox-API-Select-User': '%s' % team_member_id} 

	# Summary Item we'll return
	myPathSummary = PathSummary()
	myPathSummary.path = aPath
	myPathSummary.id = aPathID

	hasMore = True;      # Controls how long we stay in while loop loading users. 
	loopCounter = 0      # Count of how many times we hit the API 

	while hasMore:

		aResult = requests.post(aURL, headers=lHeadersTMFA, data=aData)  # List_Folders

		# If we don't get a 200 HTML response code, we didn't get a result. 
		if( aResult.status_code != 200 ):
	 		printmessageblock ('* Failed to get a response to call for list_folder. \nWe got an error [%s] with text "%s"' % (aResult.status_code, aResult.text))
	 		next;

		# Note the JSON response
		pathFilesAndFolders = aResult.json()
		pprint.pprint( pathFilesAndFolders )

		# Loop through each item in list
		for item in pathFilesAndFolders['entries']: 

			# If it's a file update our summary record
			if ( item['.tag'] == 'file'):
				myPathSummary.file_size_in_bytes += item['size']
				myPathSummary.file_folder_size_in_bytes += item['size']
				myPathSummary.num_files += 1
			
			# If it's a folder, recursively call this function
			else:
				myPathSummary.num_folders += 1
				
				summary = getSumOfPath( item['path_lower'], item['id'], aMasterFolderList, team_member_id )
				myPathSummary.file_folder_size_in_bytes += summary.file_folder_size_in_bytes
				aMasterFolderList.append( summary )


		hasMore = pathFilesAndFolders['has_more']            # Note if there's another cursor call to make. 

		# If it's the first run, from this point onwards the API call is the /continue version.
		if ( loopCounter >= 0 ):
			aURL = 'https://api.dropboxapi.com/2/files/list_folder/continue'
			aData = json.dumps({'cursor': pathFilesAndFolders['cursor']}) 
			loopCounter += 1

	return myPathSummary


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
# Get a list of users to analyze
# If empty or not found ask user if they want to analyze ALL
# ############################################
"""

gUsersToAnalyze = []
bAnalyzeAll = False

# Check we have a Domains file
bHaveCSV = os.path.isfile( sourceMembersToReportOn ) 

if (not bHaveCSV):
	print('We could not find a file listing users to report on. ')
	print('Would you like to analyze ALL users on the team. Note this could be a very slow process.') 
	lsAnswer = input("Type 'y' to process ALL or 'n' to cancel this script: ")

	if ( lsAnswer == 'y' or lsAnswer == 'Y'):
		bAnalyzeAll = True
	elif ( lsAnswer == 'n' or lsAnswer == 'N'): 
		print( '\nExiting script\n')
		exit()
	else:
		print("\n\nUser did not enter a 'n' or a 'y' input. Ending script.")
		exit();

if (not bAnalyzeAll):
	# Open file of users to analyze
	with open( sourceMembersToReportOn, 'rt') as csvfileRead:
		# Open file to read from
		reader = csv.reader(csvfileRead)

		#Iterate through each row of the CSV.
		for row in reader:
			gUsersToAnalyze.append( row[0].lower() ) # Lower case so we can compare to Dropbox ( always lowercase )

		if ( len(gUsersToAnalyze) <= 0 ):

			# Check that we have users
			print("We could not any users in file '%s' to report on. " % sourceMembersToReportOn)
			print('Would you like to analyze ALL users on the team. Note this could be a very slow process.') 
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
# ############################################
# Step 2
# 1. Check if we have the necessary Tokens.
# 2. If not, ask the user to enter it.
# ############################################
"""
if (gTokenTMFA == ''):
  gTokenTMFA = raw_input('Enter your Dropbox Business API App token (Team Member File Access permission): ')

if (gTokenTMM == ''):
  gTokenTMM = raw_input('Enter your Dropbox Business API App token (Team Member Management permission): ')


# Note the standard output
gstdout = sys.stdout
# Redirect standard output to log file
sys.stdout = open('logfile.txt', 'w')


"""
#############################################
# Step 3
# 1. Get a list of all Team Folders
#############################################
"""
aHeaders = {'Content-Type': 'application/json', 
		'Authorization': 'Bearer %s' % gTokenTMFA}
aURL = 'https://api.dropboxapi.com/2/team/team_folder/list'
aData = json.dumps({'limit': 300}) 

hasMore = True;      # Controls how long we stay in while loop loading users. 
loopCounter = 0      # Count of how many times we hit the API 
dbxTeamFolders = []        # List of Dropbox Users
dbxTFLookup = {}  # A quick reference list of key-pair values of team-member-ids and email addressses 


print ("> Retrieving Team Folders via API")
timestart = datetime.datetime.fromtimestamp(time.time())			# Used to note start and calculate total time script took to run.

while hasMore:

	print (">>> API call")
	""" Make the API call """ 
	aResult = requests.post(aURL, headers=aHeaders, data=aData)

	print ("<<< Results")

	# If we don't get a 200 HTML response code, we didn't get a result. 
	if( aResult.status_code != 200 ):
		print ('>>> Failed to get a response to call for /team/team_folder/list')
		print (aResult.text)
		exit();

	# Note the JSON response
	teamFolders = aResult.json()

	# Iterate over the Members in the JSON
	for aTeamFolder in teamFolders['team_folders']:
		dbxTeamFolders.append( aTeamFolder )
		dbxTFLookup[ aTeamFolder['team_folder_id'] ] = aTeamFolder['name'] 
		print ( aTeamFolder['team_folder_id'] + " : " + aTeamFolder['name'] )

	hasMore = teamFolders['has_more']            # Note if there's another cursor call to make. 

	# If it's the first run, from this point onwards the API call is the /continue version.
	if ( loopCounter >= 0 ):
		aURL = 'https://api.dropboxapi.com/2/team/team_folder/list/continue'
		aData = json.dumps({'cursor': teamFolders['cursor']}) 
		loopCounter += 1






"""
#############################################
# Step 3
# 1. Setup the necessary variables to get list of members. 
#############################################
"""
aHeaders = {'Content-Type': 'application/json', 
		'Authorization': 'Bearer %s' % gTokenTMM}
aURL = 'https://api.dropboxapi.com/2/team/members/list'
aData = json.dumps({'limit': 300}) 



"""
#############################################
# Step 4
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

print (" We have " + str(len(dbxUsers)) + " Dropbox Team members in memory from " + str(loopCounter) + " API Calls. it took " + str((timestop-timestart).total_seconds()) + " seconds.\n\n") 




#############################################
# Step 5
# Iterate over the members
# Check if we're analyzing all users
# If yes, then go ahead
# If not, then check if member in list to analyse
############################################
summaryReport = []



with open( 'Report.csv', 'wt') as csvReportSummary:

	writerSummary = csv.writer(csvReportSummary, delimiter=',')
	writerSummary.writerow(['Email Address', 'Folder Path', 'Path ID', 'Total bytes in folder and sub-folders', 'Total bytes - Human Readable', 'Size of bytes in folder', 'No. Files in folder' , 'No. Folders in folder' ])

	aCounter = 1

	for aMember in dbxUsers:

		# Check if we're analyzing specific users
		if (not bAnalyzeAll):
			# Check if this member in csv list
			if ( str(aMember['profile']['email']).lower() not in gUsersToAnalyze ):
				continue;


		print( 'Processing user %s of %s: %s' % (aCounter, len(dbxUsers),aMember['profile']['email']))
		aCounter += 1
		
		timeStart = datetime.datetime.fromtimestamp(time.time())

		aMasterFolderList = []
		aMasterFolderList.append( getSumOfPath('', '', aMasterFolderList, str(aMember['profile']['team_member_id'])) )
		
		# Counters for second report
		summaryUserBytesTotal = 0
		summaryUserTotalFiles = 0
		summaryUserTotalFolders = 0

		for item in aMasterFolderList:
			writerSummary.writerow([aMember['profile']['email'],item.path, item.id, item.file_folder_size_in_bytes, getBytesAsGB_MB_KB(item.file_folder_size_in_bytes), item.file_size_in_bytes, item.num_files, item.num_folders])
			
			# Spin out a second report a flat summary of user account
			summaryUserTotalFiles  += item.num_files
			summaryUserTotalFolders += item.num_folders


			if ( item.path.count("/") == 0):
				summaryUserBytesTotal += item.file_folder_size_in_bytes

		
		summaryReport.append( [aMember['profile']['email'], summaryUserBytesTotal, summaryUserTotalFiles, summaryUserTotalFolders] )


		timeStop = datetime.datetime.fromtimestamp(time.time())
		userTimeInSeconds = (timeStop-timeStart).total_seconds()
		print( 'User %s took %s' % (aMember['profile']['email'], getTimeInHoursMinutesSeconds( userTimeInSeconds )))



with open( 'ReportSummary.csv', 'wt') as csvReportSummary:
	writerSummary = csv.writer(csvReportSummary, delimiter=',')
	writerSummary.writerow(['Email Address', 'Total bytes', 'Total bytes - Human Readable', 'No. Files' , 'No. Folders' ])

	for item in summaryReport:
		writerSummary.writerow([item[0],item[1], getBytesAsGB_MB_KB(item[1]), item[2], item[3]])
			

with open( 'TeamFolders.csv', 'wt') as csvReportSummary:
	writerSummary = csv.writer(csvReportSummary, delimiter=',')
	writerSummary.writerow(['Team Folder Name', 'ID', 'Status', 'Team Shared Dropbox', 'Admin Sync Setting' ])

	for item in dbxTeamFolders:
		writerSummary.writerow([item['name'], item['team_folder_id'], item['status']['.tag'], item['is_team_shared_dropbox'], item['sync_setting']['.tag'] ])


"""
#############################################
# Step 6
# 1. Output how long the script took to run.
#############################################
"""
totalTimeStop = datetime.datetime.fromtimestamp(time.time())
totalTimeInSeconds = (totalTimeStop-totalTimeStart).total_seconds()
timeAsStr = getTimeInHoursMinutesSeconds( totalTimeInSeconds )
printmessageblock( " Script finished running, it took %s seconds." % ( timeAsStr ) )
