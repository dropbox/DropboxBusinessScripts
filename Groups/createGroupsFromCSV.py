from __future__ import print_function
import json
import requests
import os                             # Allows for the clearing of the Terminal Window
import csv                            # Allows outputting to CSV file
import time, datetime


"""
********************************************************************************************************************

The intention of this script is to:

Load a CSV file of groups to be created into a Dropbox Team account. 
The script assumes the file is in the same location as the executing python script. 

You need to provide three inputs into the variables below.
1. Team Member Management token
2. The name of the source file
3. Whether the groups are created as 'company_managed' or 'user_managed' groups
	  user_managed    = A group which is managed by selected users.
	  company_managed = A group which is managed by team admins only.
4. If the script tried to create a group that already exists in Dropbox, it will note it and output all failures
   to a csv file called 'failedToCreateGroups.csv'


********************************************************************************************************************
"""




"""
Set your OAuth Token here with 'Team Member Management' permissions
"""
gTokenTMM = ''    	# Team Member Management    
gSourceFile = 'groups.csv'							# source file with names of groups to create
gGroupManagementType = 'company_managed'			# user_managed = A group which is managed by selected users.






"""
********************************************************************************************************************
                                             DO NOT EDIT BELOW THIS POINT
********************************************************************************************************************
"""

# Note the time we start the script
totalTimeStart = datetime.datetime.fromtimestamp(time.time())

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
# Step 0
# Clear the terminal window, not essential but makes it easier to read this way.
#############################################

os.system('cls' if os.name=='nt' else 'clear')



#############################################
# Step 1
# Check file exists to ensure there's something to work off
#############################################

bHaveXLSX = os.path.isfile( gSourceFile )

if ( bHaveXLSX is False ):
	print('>>> Can not find the source file %s, exiting the script.\n' % gSourceFile);
	exit();



#############################################
# Step 2
# Open the source file.
# For each row it the file create a group in Dropbox Account
#############################################

createdGroupsCnt = 0
failedGroups = []        # List of Groups we couldn't create

aURL = 'https://api.dropboxapi.com/2/team/groups/create'
aHeaders = {'Content-Type': 'application/json', 'Authorization': 'Bearer %s' % gTokenTMM}

with open( gSourceFile, 'rb') as csvfileRead:
	# Open file to read from
	reader = csv.reader(csvfileRead)
	
	#Iterate through each row of the CSV.
	for row in reader:

		# Set up the call to create new group name
		aData = json.dumps({'group_name': row[0], 'group_management_type': gGroupManagementType}) 

		print ('>>> API call - Create Group: %s' % row[0])
		aResult = requests.post(aURL, headers=aHeaders, data=aData)
		print ('<<< Results')

		if ( aResult.status_code == 200):
			createdGroupsCnt += 1
		else:
			# If we get a 409 HTML response code, group already exists. 
			if( aResult.status_code == 409 ):
				failedGroups.append( row[0] )
			else:
				print ('* Failed with call to Create Group "%s". \nWe got an error [%s] with text "%s"' % (row[0], aResult.status_code, aResult.text))
		

#############################################
# Step 3
# If we got failures to create, output to a csv file.
#############################################

if ( len(failedGroups) > 0 ):

	with open( 'failedToCreateGroups.csv', 'wt') as csvfile:

		# Define the delimiter
		writer = csv.writer(csvfile, delimiter=',')

		for item in failedGroups:
			writer.writerow( [item] )


"""
#############################################
# Step 4
# Output how long the script took to run.
#############################################
"""

print( '\n\n%s groups cretaed.' % createdGroupsCnt)
print( '%s groups failed to create ' % len(failedGroups) )

totalTimeStop = datetime.datetime.fromtimestamp(time.time())
totalTimeInSeconds = (totalTimeStop-totalTimeStart).total_seconds()
timeAsStr = printTimeInHoursMinutesSeconds( totalTimeInSeconds )
print( "\n\nScript finished running, it took %s seconds." % ( timeAsStr ) )
