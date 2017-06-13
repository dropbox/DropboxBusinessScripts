import json
import requests
import os                             # Allows for the clearing of the Terminal Window
import csv                            # Allows outputting to CSV file
import time, datetime 
import argparse

"""
A Script to compare the members of a Dropbox Account to a CSV file of OLD to NEW email addresses.

For every user in the Dropbox Account, excluding those ending in domain to be optionally filtered out
by variable 'filterOut', it looks for the email address in CSV list of OLD addresses, row index [0]. 
If found, it updates the Dropbox account to use the 'NEW' email address, row index [1]. 
Email address in CSV source file will be converted to lowercase for comparison to Dropbox, as emails in Dropbox are all lowercase. 

The following output files are created. 

YY-MM-DD-converted.csv   			     -> List of users in Dropbox account converted to NEW email addresses.
YY-MM-DD-failedconversion.csv 		     -> List of users we TRIED to convert but it failed for some reason. ( non 200 API response )
YY-MM-DD-notFoundInSourceFile.csv        -> List of users that exist in Dropbox but who's email addresses not found in CSV source emails.
YY-MM-DD-sourceItemNotFoundInDropbox.csv -> List of users from source file not found in Dropbox. 
YY-MM-DD-filteredOut.csv     		     -> List of users in Dropbox account who's email addresses skipped as match the 'filterOut' condition
YY-MM-DD-oldEqualsNew.csv                -> List of users we found in Dropbox and Source email list, but who's NEW email address is same as old.
"""





"""
Set your OAuth Token here with 'Team Member Management' permissions
"""
aToken = ''     # Team Member Management Dropbox API OAuth Token
sourceFile = 'csv-source.csv'							# (Do not give a folder path) File should reside in same folder as script. Format: From Email, To Email
filterOut = ''		                                    # OPTIONAL!! For when iterating through Dropbox Accounts we don't want to change '@example.com' accounts.
mockRun = False                                         # If True the script emulates the actual call to the API so no email addresses actually change.




"""
DO NOT EDIT BELOW THIS POINT
"""

#############################################
# Handle the '-h' or '--help' arguments
#############################################
parser = argparse.ArgumentParser(
	description='Converts a CSV list of users from one email address to another email address in a Dropbox Team account.' +
	'\n\n Requires a Dropbox API Team Member Management OAuth Token. This and the name of source CSV file can be set in the top of the script. \n ')

args = parser.parse_args()

#############################################
# Function to return current Timestamp 
#############################################
def getTimeYMD():
  lRightNow = datetime.datetime.fromtimestamp(time.time()).strftime('%Y%m%d') 
  return lRightNow;

#############################################
# Function to write out to file
#############################################
def writeToFile( fileName, listToWrite ):
  
    newFileName = ("%s-" + fileName) % getTimeYMD()

    with open( newFileName, 'wt') as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        # Write the Column Headers
        writer.writerow(['email address','team member id'])

        for item in listToWrite:
            writer.writerow([item[0],item[1]])

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
# Define the API endpoint and limit of results per query
#############################################
aURL = 'https://api.dropboxapi.com/2/team/members/list'
aData = json.dumps({'limit': 200}) 

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
if (aToken == ''):
  aToken = raw_input('Enter your Dropbox Business API App token (Team Member Management permission): ')

aHeaders = {'Content-Type': 'application/json', 'Authorization': 'Bearer %s' % aToken}



"""
#############################################
# Step 2
# 1. Check if there a source CSV File to read
#    ADFS from/to email addresses from. 
# 2. Exit if we don't
#############################################
"""

if not os.path.exists(sourceFile):
	print (">>> Can't find source file %s. Exiting script.") % sourceFile
	exit()

"""
#############################################
# Step 3
# 1. Open the file and iterate over each row
# 2. Add the User to a Key Value Dictionary.
#############################################
"""

userList = {}
timestart = datetime.datetime.fromtimestamp(time.time())
cnt = 0

with open( sourceFile, 'rb') as csvfile:
#with open( sourceFile, 'rt', encoding='ISO-8859') as csvfile:
	fileReader = csv.reader(csvfile, delimiter=',')
	for row in fileReader:
		userList[row[0].lower()] = row[1].lower()
		cnt += 1

timestop = datetime.datetime.fromtimestamp(time.time())

print ("> We have the CSV file in memory. %s items and it took %s") % (cnt, getTimeInHoursMinutesSeconds((timestop-timestart).total_seconds()))
# We now have an in memory copy of the file


"""
#############################################
# Step 4
# 1. Get list of all Dropbox Team Members
# 2. Create in memory list of them.
# 3. If they match variable 'filterOut', skip them and move to skipped list.
#############################################
"""
hasMore = True;
loopCounter = 0 
dbxUsers = []
skippedExistingUsers = []   # List of users in Dropbox who's email matches the variable filterOut

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
		# Check if they have an email address matching 'filterOut' if so skip them
		if ( filterOut != "" and aMember['profile']['email'].endswith( filterOut ) ):
			skippedExistingUsers.append( [aMember['profile']['email'], aMember['profile']['team_member_id']] )
		else:
			dbxUsers.append( [aMember['profile']['email'], aMember['profile']['team_member_id']] )

	hasMore = members['has_more']            # Note if there's another cursor call to make. 

	# If it's the first run, from this point onwards the API call is the /continue version.
	if ( loopCounter >= 0 ):
		aURL = 'https://api.dropboxapi.com/2/team/members/list/continue'
		aData = json.dumps({'cursor': members['cursor']}) 
		loopCounter += 1

timestop = datetime.datetime.fromtimestamp(time.time())
print (" We have the Dropbox users in memory from %s API Calls. it took %s") % (loopCounter,getTimeInHoursMinutesSeconds((timestop-timestart).total_seconds()))




"""
#############################################
# Step 5
# 1. Iterate through List of Dropbox Users
# 2. Look for them in Source File
# 3. If they exist with alternate email address, change it in Dropbox, move to converted list.
#############################################
"""

notFoundInSource = []   # List of users in Dropbox who's email can't be found in Source
sourceNotFoundInDBX = [] # List of email addresses in source file not found in Dropbox
convertedUsers = []
failedToConvert = []
oldEqualsNew = []
dbxUsersList = {}

countConverted = 0

totalStartTime = datetime.datetime.fromtimestamp(time.time())

# Iterate through Dropbox List
for member in dbxUsers:
	
	# Check for Dropbox User in Source list
	newEmailAddr = userList.get( member[0] )

	dbxUsersList[member[0]] = member[0]

	# If we can't find it there... 
	if newEmailAddr is None:
		notFoundInSource.append( [member[0], member[1]] )
	else:
		# Check if the OLD and NEW are the same, no point converting if that's the case
		if (newEmailAddr == member[0]):
			oldEqualsNew.append ([member[0], newEmailAddr])
		else:
			# If email address exists in Conversion Source file, do the conversion!
			print ("\nFound a match: %s " % member[0] )
			aURL = "https://api.dropboxapi.com/2/team/members/set_profile"
			aData = json.dumps({'user': {'.tag': 'team_member_id', 'team_member_id': member[1]}, 'new_email': newEmailAddr}) 
			
			timestart = datetime.datetime.fromtimestamp(time.time())
			print ("+")
			""" Make the API call """ 
			if (mockRun == True):
				print "_____MOCK RUN - NO API CALL MADE_____"
				time.sleep(0.002)
			else:
				aResult = requests.post(aURL, headers=aHeaders, data=aData)
			
			timestop = datetime.datetime.fromtimestamp(time.time())
			print ("+++ %s seconds") % (timestop-timestart).total_seconds()

			# Check API ran correctly
			if( aResult.status_code == 200 ):
				# Add user to converted list
				convertedUsers.append ( [ member[0], newEmailAddr]) #, member[1]
				countConverted += 1
				print ("Converted user from: %s   to   %s") % (member[0], newEmailAddr)
			else:
				failedToConvert.append ( [newEmailAddr, member[1]])
				print ("Failed to convert %s due to error %s: %s") % ( newEmailAddr, aResult.status_code, aResult.text ) 

totalStopTime = datetime.datetime.fromtimestamp(time.time())


# Lastly, iterate once more through source file list and see if any don't exist in list of Dropbox Members
for user in userList:

	# try locate in dbxUsers
	match = dbxUsersList.get( user )

	if match is None:
		if ( not user == 'emailaddress' ):
			sourceNotFoundInDBX.append( [user, ''] )




# Print total time taken to run through and convert users
print ("\n\n*******************************************************")
print ("Total Time to convert: %s ") % getTimeInHoursMinutesSeconds((totalStopTime-totalStartTime).total_seconds())
print ("*******************************************************")


print ("\nResults:")

# Write List of Users Converted to File
if convertedUsers != []:
	writeToFile( 'converted.csv', convertedUsers )
	print (" - Converted %s users") % len(convertedUsers)

# Write List of Users we tried to convert but failed for some reason!
if failedToConvert != []:
	writeToFile( 'failedconversion.csv', failedToConvert )
	print (" - Failed to convert %s users") % len(failedToConvert)

# Write List of Users Skipped to File
if skippedExistingUsers != []:
	writeToFile( 'filteredOut.csv', skippedExistingUsers )
	print (" - Skipped %s users") % len(skippedExistingUsers)

# Write List of Users Not Found to File
if notFoundInSource != []:
	writeToFile( 'notFoundInSourceFile.csv', notFoundInSource )
	print (" - Couldn't find %s Dropbox users in source file") % len(notFoundInSource)

# Write List of Users in source file but not found in Dropbox
if sourceNotFoundInDBX != []:
	writeToFile( 'sourceItemNotFoundInDropbox.csv', sourceNotFoundInDBX )
	print (" - Couldn't find %s email address from Sourcefile in Drobpox.") % len(sourceNotFoundInDBX)

# Write List of Users who's old email address is same as new
if oldEqualsNew != []:
	writeToFile( 'oldEqualsNew.csv', oldEqualsNew )
	print (" - Skipped coverting %s users as old and new emails the same.") % len(oldEqualsNew)

# End of script

print ('\n>>> Script Complete <<<\n')
