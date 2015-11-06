import urllib2
import json
import re
import csv
import argparse

# Look up a member id from an email address
def getMemberId(token, email):
    lookupRequest = urllib2.Request('https://api.dropbox.com/1/team/members/get_info', json.dumps({'email': email }))
    lookupRequest.add_header("Authorization", "Bearer "+token)
    lookupRequest.add_header("Content-type", 'application/json')
    profile = json.loads(urllib2.urlopen(lookupRequest).read())
    return  profile['profile']['member_id']

# Give an member admin permissions
def grantAdmin(token, memberId):
    if memberId is None:
        return
    addRequest = urllib2.Request('https://api.dropbox.com/1/team/members/set_permissions', json.dumps({'member_id': memberId, 'new_is_admin':True }))
    addRequest.add_header("Authorization", "Bearer "+token)
    addRequest.add_header("Content-type", 'application/json')
    urllib2.urlopen(addRequest);
    print "    granted admin permissions"


# Command line arguments
parser = argparse.ArgumentParser(description='Invites Dropbox for Business members from a CSV file.')
parser.add_argument('file', type=argparse.FileType('r'), help='CSV File of users to provision. Format is [email,firstname,lastname]')
parser.add_argument( '-s', '--silent', action='store_const', const=True, default=False, dest='silent', help='Silent invite. Skips welcome email.')
parser.add_argument( '-a', '--admin', action='store_const', const=True, default=False, dest='admin', help='Grants admin permissions to invited members.')

args = parser.parse_args()

dfbToken = raw_input('Enter your Dropbox Business API App token (Team Member Management permission): ')

if args.silent:
    print "Starting silent provision"
else:
    print "Starting provision"

csvreader = csv.reader(args.file)
for row in csvreader:

    # Check for 3 columns, make sure first column looks like an email. Terminate with script help if not.
    if not len(row) == 3:
        parser.error("Expected 3 column CSV file in the format [email,firstname,lastname]. Error in line "+row)
    if not re.match("[^@]+@[^@]+\.[^@]+", row[0]):
        line = ','.join(row)
        parser.error("Expected 3 column CSV file in the format [email,firstname,lastname]. Invalid email in line ["+line+"]")
        
    # Add the member
    welcome = not args.silent
    addRequest = urllib2.Request('https://api.dropbox.com/1/team/members/add', json.dumps({'member_email': row[0], 'member_given_name': row[1], 'member_surname': row[2], 'send_welcome_email':welcome}))
    addRequest.add_header("Authorization", "Bearer "+dfbToken)
    addRequest.add_header("Content-type", 'application/json')
    
    try:
        print "  inviting "+row[0]
        profile = json.loads(urllib2.urlopen(addRequest).read())
        if args.admin:        
            grantAdmin(token=dfbToken, memberId=profile['profile']['member_id'])
        
    except urllib2.HTTPError, error:
        msg = json.loads(error.read())["error"]        
                
        # If OAuth token is bad (401) or doesn't have member management permission (403), terminate & display script help.
        if error.code == 401 or error.code == 403:
            parser.error(msg)

        # If the member has already been invited        
        if (msg == 'user_already_on_team'):
            print "    user is already invited to the DfB team"
            
            member_id = getMemberId(token=dfbToken, email=row[0])
                
            # re-send the invite if we're not in silent mode
            if not args.silent:
                welcomeRequest = urllib2.Request('https://api.dropbox.com/1/team/members/send_welcome_email', json.dumps({'member_id': member_id }))
                welcomeRequest.add_header("Authorization", "Bearer "+dfbToken)
                welcomeRequest.add_header("Content-type", 'application/json')
                urllib2.urlopen(welcomeRequest).read()
                print "    re-sent invitation"

            # grant the admin
            if args.admin:
                grantAdmin(token=dfbToken, memberId=member_id)
                
        else:        
            print "    error: "+msg

print "Done"
