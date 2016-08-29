# Deprovision users from CSV with option to change their email and let the keep their account as Dropbox Basic

import urllib2
import json
import re
import csv
import argparse

# Command line arguments
parser = argparse.ArgumentParser(description='Removes Dropbox Business members from a CSV file.')
parser.add_argument('file', type=argparse.FileType('r'), help='CSV File of users to provision. '
                                                              'Format is [email,keep account (true/false),'
                                                              'new email (optional)]')
args = parser.parse_args()

token = raw_input('Enter your Dropbox Business API App token (Team Member Management permission): ')


# set new email for the user to use post deprovision
def setEmail(oldEmail, newEmail):

    data = {
        "user": {
            ".tag": "email",
            "email": oldEmail
        },
        "new_email": newEmail
    }

    request = urllib2.Request('https://api.dropboxapi.com/2/team/members/set_profile', json.dumps(data))
    request.add_header("Authorization", "Bearer " + token)
    request.add_header("Content-type", 'application/json')

    try:
        json.loads(urllib2.urlopen(request).read())

    # Exit on error here.  Probably user not found or bad OAuth token.  Show response.
    except urllib2.HTTPError, error:
        print 'Error setting ' + oldEmail + ' to ' + newEmail + ': ' + str(error.read())


# remove member, letting them keep their account (true/false), and wipe their devices (true/false)
def removeMember(email, keep):

    data = {
        "user": {
            ".tag": "email",
            "email": email
        },
        "wipe_data": not keep,
        "keep_account": keep
    }

    request = urllib2.Request('https://api.dropbox.com/2/team/members/remove', json.dumps(data))
    request.add_header("Authorization", "Bearer " + token)
    request.add_header("Content-type", 'application/json')

    try:
        response = json.loads(urllib2.urlopen(request).read())
        print 'Deprovisioned ' + email

    # Exit on error here.  Probably user not found or bad OAuth token.  Show response.
    except urllib2.HTTPError, error:
        print 'Error deprovisioning ' + email + ': ' + str(error.read())


for row in csv.reader(args.file):

    # Check for 3 columns, make sure first column looks like an email. Terminate with script help if not.
    if len(row) < 2:
        print "Expected 2-3 column CSV file in the format [email,keep account (true/false),new email (optional)]. " \
              "Error in line " + str(row)
    elif not re.match("[^@]+@[^@]+\.[^@]+", row[0]):
        print "Invalid email in line [" + str(row) + "]"
    elif len(row) == 3 and len(row[2]) > 0 and not re.match("[^@]+@[^@]+\.[^@]+", row[2]):
        print "Invalid new email in line [" + str(row) + "]"
    else:

        # hold onto email that needs to be removed
        email = row[0]

        # if there's a new email address, change the email first
        if len(row) > 2 and len(row[2]) > 0:
            setEmail(row[0], row[2])
            email = row[2]

        # Remove the member
        removeMember(email, str.lower(row[1]).strip() == 'true')

