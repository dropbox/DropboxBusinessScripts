#!/usr/bin/python
# -*- coding: latin-1 -*-

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
--NOTE--
This script is a working example of how you might permanently delete content, it is not recommended that you permanently delete data
without testing and confirming it's what you want to do. You can not undo this. You can not recover the permanently deleted data.
Script runs in 'testmode' unless you edit the script to do otherwise. 
Run at your own risk!

--> Folders with more than 5000 files in it will not be deleted. 
--> Folders with sub-folders that couldn't be deleted won't be deleted. 
--> logfile.txt is where console/print commands are placed. 
--> Report.csv is where details of folders and what was deleted or not. 

--WHAT DOES SCRIPT DO?--
This script iterates through a csv list, each line represents a member of a team. For each member uses the 
provided path given as the starting point to delete the folder and all sub-folders/files from Team Members account. 

CSV file should be called 'config.csv' listing out on separate rows the email address of each team 
member followed by the path of the folder to be deleted.
  e.g. 
  example.user@company.com,/marketing/internal assets
  another.user@company.com,/archive/videos

NOTE:
In example above the folder "/marketing" is not deleted, nor are files within that folder. Only folder "/internal assets"
      and it's sub folders/files are deleted. Same applies to example /archive.

If you do not provide a list, or the list is empty, the script will end. 
If you provide a path of /, which is the Dropbox root, the script will skip that user assuming a mistake has occurred
and will not destroy an entire account's content. 

As this could be a VERY slow process you are prompted to confirm your choice under this circumstance.

Outputted file is 'report.csv' pre-fixed with date and time. 

It has the following column headers:
  Folder Path: Path to a folder within or the path specified in source CSV file itself. 
  Number of folders: Number of sub-folders one level below the path ( does not include sum of subsequent sub-folders )
  Number of files: Number of files one level below the path ( does not include sum of subsequent sub-folders )
  Total size in Folder structure: Total volume of information below this path structure
  Total bytes in folder structure: Total volume of information below this path structure in bytes
  File size in folder: Total volume of files in the path ( does not include sum of subsequent sub-folders  )
  File bytes in folder: Total volume of files in the path in bytes
  Path Deleted: Where we able to delete the path?

--REQUIREMENTS--
  Script written testing on Python 2.7.10

  Two Dropbox API Tokens are needed, insert just below this comments section.
  * Team Member File Access
  * Team Member Management

--PRE-REQUISITES--
  * Script requires library 'requests' to make API calls. Navigate to python scripts folder e.g. c:\Python27\Scripts
  * Then run command "pip install requests"
  Note: if experiencing issues installing libraries try append " --user" to end of each pip command

--TO DO--
  * Set your Team Member Management token
  * Set your Team Member File Access token
  * Create a file called 'config.csv' in same folder as this script, add member emails and folder to PERMANENTLY delete. 
 
"""





"""
Set your OAuth Tokens here
"""
gTokenTMM = ''    	# Team Member Management 
gTokenTMFA = ''     # Team Member File Access

# Source File Here
gListOfMembersToReportOn = 'config.csv'


# Flag to control actually permanently deleting data. If set to 'False' will PERMANENTLY delete content!
gRunInTestMode = True









"""
DO NOT EDIT BELOW THIS POINT
"""

# A variable to manage the cut off point beyond which we don't delete files
gFileCountLimitForDeletions = 5000 
gListFolderLimit = 1000

totalTimeStart = datetime.datetime.fromtimestamp(time.time())


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
# Class to represent a summary of path details
#############################################
class PathSummary:
	def __init__(self):
		self.memberEmail = ''
		self.path = ''
		self.file_size_in_bytes = 0
		self.file_folder_size_in_bytes = 0
		self.num_files = 0
		self.num_folders = 0
		self.deleted = False
		self.not_found = False

	def asString(self):
		result = self.memberEmail +', ' + self.path + ', ' + str(self.num_folders) + ', ' + str(self.num_files) + ', "' + getBytesAsGB_MB_KB(self.file_folder_size_in_bytes) + '", ' 
		result += str(self.file_folder_size_in_bytes) + ', "' + getBytesAsGB_MB_KB(self.file_size_in_bytes) + '", ' + str(self.file_size_in_bytes) + ', '
		result += str(self.deleted)

	def asArray(self):
		result = [self.memberEmail, self.path, str(self.num_folders), str(self.num_files), '"' + getBytesAsGB_MB_KB(self.file_folder_size_in_bytes) + '"',  
		         str(self.file_folder_size_in_bytes), '"' + getBytesAsGB_MB_KB(self.file_size_in_bytes) + '"',  str(self.file_size_in_bytes), 
		         str(self.deleted) ]

		return result

#############################################
# Function to print Message to console in a tidy box
#############################################
def printmessageblock( str ):
  print "\n*********************************************************"
  print "* %s" % (str)
  print "*********************************************************\n"
  return;

#############################################
# Function to print Message to console in a tidy box
#############################################
def printTimeInHoursMinutesSeconds( sec ):
    sec = int(sec)
    hrs = sec / 3600
    sec -= 3600*hrs

    mins = sec / 60
    sec -= 60*mins

    return '%s hrs, %s mins, %s sec' % ( hrs, mins, sec);

#############################################
# Method to permanently delete a folder path
#############################################
def permanentlyDeletePath(path, team_member_id):

	aURL = "https://api.dropboxapi.com/2/files/permanently_delete"
	aData = json.dumps({"path":path.strip()})
	lHeadersTMFA = {'Content-Type': 'application/json',
		'Authorization': 'Bearer %s' % gTokenTMFA, 
		'Dropbox-API-Select-User': '%s' % team_member_id} 

	aResult = None

	if (not gRunInTestMode):
		aResult = requests.post(aURL, headers=lHeadersTMFA, data=aData)  # Permanently Delete Data
	else:
		print ( "Test Run call to Permanently Delete path %s" % path )
		return True

	if( aResult.status_code != 200 ):
		print ( "ERROR: Failed to delete %s with error code %s, '%s'" % (path, aResult.status_code, aResult.text))
		return False

	return True


#############################################
# Recursive Function to take a path and analyse
# it and it's child folders
#############################################
def deletePath(aMemberEmail, aPath, aMasterFolderList, team_member_id):

	aURL = 'https://api.dropboxapi.com/2/files/list_folder'
	aData = json.dumps({'path': aPath.strip(),
		'recursive': False, 
		'include_media_info': False,
		'include_deleted': False,
		'include_has_explicit_shared_members': False,
		'include_mounted_folders': True,
		'limit': gListFolderLimit}) 

	lHeadersTMFA = {'Content-Type': 'application/json',
		'Authorization': 'Bearer %s' % gTokenTMFA, 
		'Dropbox-API-Select-User': '%s' % team_member_id} 

	# Summary Item we'll return
	myPathSummary = PathSummary()
	myPathSummary.memberEmail = aMemberEmail
	myPathSummary.path = aPath

	hasMore = True;      # Controls how long we stay in while loop loading users. 
	loopCounter = 0      # Count of how many times we hit the API 

	while hasMore:

		aResult = requests.post(aURL, headers=lHeadersTMFA, data=aData)  # List_Folders

		# If we don't get a 200 HTML response code, we didn't get a result. 
		if( aResult.status_code != 200 ):
	 			 		
	 		# Check if path not found, we may have already deleted it!!
	 		if ( 'not_found' in aResult.text ):
	 			print( '----Path "%s" not found, assume already deleted perviously in script.' % aPath )
	 			myPathSummary.not_found = True
	 		else:
	 			printmessageblock ('* Failed to get a response to call for list_folder on path "%s". \nWe got an error [%s] with text "%s"' % (aPath.strip(), aResult.status_code, aResult.text))
	 		
	 		
	 		return myPathSummary

		# Note the JSON response
		pathFilesAndFolders = aResult.json()

		# Loop through each item in list
		for item in pathFilesAndFolders['entries']: 

			# If it's a file update our summary record
			if ( item['.tag'] == 'file'):
				myPathSummary.file_size_in_bytes += item['size']
				myPathSummary.file_folder_size_in_bytes += item['size']
				myPathSummary.num_files += 1
			
			# If it's a folder, recursively call this function
			else:
				summary = deletePath( aMemberEmail, item['path_lower'], aMasterFolderList, team_member_id )
				
				# Check if we deleted sub-folder
				if (summary.deleted != True):
					# Check if we found folder, don't count if not. 
					if(summary.not_found != True):
						myPathSummary.num_folders += 1
						myPathSummary.file_folder_size_in_bytes += summary.file_folder_size_in_bytes

				# Check if we found folder, don't count if not. 
				if(summary.not_found != True):
					aMasterFolderList.append( summary )


		hasMore = pathFilesAndFolders['has_more']            # Note if there's another cursor call to make. 

		# If it's the first run, from this point onwards the API call is the /continue version.
		if ( loopCounter >= 0 ):
			aURL = 'https://api.dropboxapi.com/2/files/list_folder/continue'
			aData = json.dumps({'cursor': pathFilesAndFolders['cursor']}) 
			loopCounter += 1

	# Check if we can delete folder, i.e. there's no SUB-FOLDERS
	print ( "\nPath: %s" % myPathSummary.path )
	print ( 'Num Folders: %s' % myPathSummary.num_folders )
	print ( 'Num Files: %s' % myPathSummary.num_files )
	if ( myPathSummary.num_folders == 0 and myPathSummary.num_files < gFileCountLimitForDeletions ):
		print( ">>> Deleting Folder %s" % myPathSummary.path)
		# Call deletion
		if ( not gRunInTestMode):
			deleteResult = permanentlyDeletePath( myPathSummary.path, team_member_id )
			
			if (deleteResult==True):
				print( "<<< Deleted Folder %s" % myPathSummary.path )
				# Update myPathSummary to reflect deletion
				myPathSummary.deleted = True
			
		else:
			print( "<<< TEST RUN Deleted Folder %s" % myPathSummary.path )
			myPathSummary.deleted = True

	else:
		if (myPathSummary.num_folders > 0):
			if (myPathSummary.num_files > gFileCountLimitForDeletions):
				# We have both Sub Folders and more Files in this folder than limit for deletion
				print("    !!! There's sub folders and > %s files in this folder preventing deletion." % gFileCountLimitForDeletions)
			else:
				# We have Sub Folders which we couldn't delete
				print("    !!! There's > %s sub folders in this folder preventing deletion." % myPathSummary.num_folders)
		else:
			if (myPathSummary.num_files > gFileCountLimitForDeletions):
				# We have more Files in this folder than limit for deletion
				print("    !!! There's > %s files in this folder preventing deletion." % gFileCountLimitForDeletions)


	return myPathSummary





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
# Get a list of users and the folder to permanently delete
# If empty or not found script will stop running.
# Finally prompt user with confirmation to begin as this could be a SLOW process.
# ############################################
"""


gUsersToAnalyze = []
bAnalyzeAll = False

# Check we have a config file
bHaveCSV = os.path.isfile( gListOfMembersToReportOn ) 

if (not bHaveCSV):
	printmessageblock('We could not find config file listing users to work on. Ending script! ')
	print ( "Stopping: %s" % getPrettyTime() )
	exit();

# Open file of users to analyze
with open( gListOfMembersToReportOn, 'rb') as csvfileRead:
	# Open file to read from
	reader = csv.reader(csvfileRead)

	#Iterate through each row of the CSV.
	for row in reader:
		gUsersToAnalyze.append( [row[0].lower(),row[1].lower()] ) # Lower case so we can compare to Dropbox ( always lowercase )

	if ( len(gUsersToAnalyze) <= 0 ):

		# Check that we have users
		printmessageblock("We could not find any users in config file '%s' to work on. Ending script." % aListOfMembersToReportOn)
		print ( "Stopping: %s" % getPrettyTime() )
		exit();

	print('This could be a very slow process. Do you wish to continue?') 
	lsAnswer = raw_input("Type 'y' to continue or 'n' to cancel this script: ")

	if ( lsAnswer == 'y' or lsAnswer == 'Y'):
		print ( 'Starting run, see log file or report for further outputs.')
	elif ( lsAnswer == 'n' or lsAnswer == 'N'): 
		print( '\nExiting script\n')
		exit()
	else:
		print("\n\nUser did not enter a 'y' or a 'n' input. Ending script.\n\n")
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



"""
# ############################################
# Step 3
# 1. Log all 'prints' to LogFile rather than console
# ############################################
"""
filename  = open(getTimeYMDHM() + '-logfile.txt','w')
sys.stdout = filename


print ( "Starting: %s" % getPrettyTime() )

"""
#############################################
# Step 4
# 1. Setup the necessary variables to get member details. 
#############################################
"""
aHeaders = {'Content-Type': 'application/json', 
		'Authorization': 'Bearer %s' % gTokenTMM}
aURL = 'https://api.dropboxapi.com/2/team/members/get_info'



"""
#############################################
# Step 5
# 1. Iterate over each CSV row member
# 2. Work out there 'team_member_id'
# 3. Call recursive delete method on the folder specified
#############################################

"""

# Store what we do for reports afterwards
aListOfWhatWasNotDeleted = []


# Iterate over each member
for aMember in gUsersToAnalyze:
	# Note the Path to start deletion from 
	memberEmail = aMember[0]
	usersPath = aMember[1].strip()
	printmessageblock ("Member: %s | Path: %s" % (memberEmail, usersPath))

	# Get Team Members ID
	aData = json.dumps({"members": [{".tag": "email","email": memberEmail}]}) 

	print (">>> Getting Team Member ID for " + memberEmail)
	aResult = requests.post(aURL, headers=aHeaders, data=aData)
	print ("<<< Results in")

	# If we don't get a 200 HTML response code, we didn't get a result. 
	if( aResult.status_code != 200 ):
		print ('>>> Failed to get a result to call for /team/members/get_info user: ' + memberEmail)
		print (aResult.text)
		continue;	# Move onto next user

	# Note the JSON response
	memberDetails = aResult.json()
	
	# Note the Team Member ID
	teamMemberID = memberDetails[0]['profile']['team_member_id']

	# Call recursive method and not what happened. 
	aListOfWhatWasNotDeleted.append( deletePath(memberEmail, usersPath, aListOfWhatWasNotDeleted, teamMemberID) )



#############################################
# Step 6
# Iterate over the results and print a report
############################################

printmessageblock( "Writing Report")

with open( getTimeYMDHM() + '-Report.csv', 'wt') as csvReportSummary:

	writerSummary = csv.writer(csvReportSummary, delimiter=',')
	writerSummary.writerow(['Member Email', 'Folder Path', 'Number of folders', 'Number of files', 'Total size in Folder structure', 'Total bytes in folder structure',  'File size in folder', 'File bytes in folder', 'Path Deleted' ])


	for item in aListOfWhatWasNotDeleted:

		writerSummary.writerow(item.asArray())
		
print("Report complete.")	


"""
#############################################
# Step 7
# 1. Output how long the script took to run.
#############################################
"""
totalTimeStop = datetime.datetime.fromtimestamp(time.time())
totalTimeInSeconds = (totalTimeStop-totalTimeStart).total_seconds()
timeAsStr = printTimeInHoursMinutesSeconds( totalTimeInSeconds )
printmessageblock( " Script finished running, it took %s seconds." % ( timeAsStr ) )

print ( "\nStopping: %s" % getPrettyTime() )

