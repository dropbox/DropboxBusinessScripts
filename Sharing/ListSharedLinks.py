# Lists all active shared links

import urllib2
import json
import argparse
import sys
import csv

reload(sys)
sys.setdefaultencoding('UTF8')

parser = argparse.ArgumentParser(description='Lists all files by user in the DfB team.')
parser.add_argument('-u', '--user', dest='users', action='append', help='Target user (email address) to scan.  All team members will be returned if unspecified. You may pass multiple -u arguments.')

args = parser.parse_args()

dfbToken = raw_input('Enter your Dropbox Business API App token (Team Member File Access permission): ')


#Look up a DfB member from an email address
def getDfbMember(email):
    request = urllib2.Request('https://api.dropbox.com/1/team/members/get_info', json.dumps({'email': email}))
    request.add_header("Authorization", "Bearer "+dfbToken)
    request.add_header("Content-type", 'application/json')
    try:
        return json.loads(urllib2.urlopen(request).read())
    
    # Exit on error here.  Probably user not found or bad OAuth token.  Show DfB response.
    except urllib2.HTTPError, error:
        parser.error(error.read())


# Get all DfB members, paging through results if necessary
def getDfbMembers(cursor):    
    data = {"limit": 100}
    if cursor is not None:
        data["cursor"] = cursor
    
    request = urllib2.Request('https://api.dropbox.com/1/team/members/list', json.dumps(data))
    request.add_header("Authorization", "Bearer "+dfbToken)
    request.add_header("Content-type", 'application/json')
    try:
        response = json.loads(urllib2.urlopen(request).read())
        members = response["members"]
        
        if response["has_more"]:
            members = members + getDfbMembers(cursor=response["cursor"])

        return members
    
    # Exit on error here.  Probably bad OAuth token. Show DfB response.
    except urllib2.HTTPError, error:
        parser.error(error.read())


# List a member's shared links
def listSharedLinks(memberEmail, memberId, csvwriter):

    try:
            
        request = urllib2.Request('https://api.dropboxapi.com/2/sharing/get_shared_links', json.dumps({}))
        request.add_header("Authorization", "Bearer " + dfbToken)
        request.add_header("Content-Type", 'application/json')
        request.add_header("Dropbox-API-Select-User", memberId)

        response_string = urllib2.urlopen(request).read()
        response = json.loads(response_string)

        for link in response["links"]:
            csvwriter.writerow([memberEmail, link['path'], link['visibility']['.tag'], link['url']])
        
    except urllib2.HTTPError as error:
        csvwriter.writerow([memberEmail, error, "ERROR", memberId])
        sys.stderr.write("  ERROR: {}\n".format(error))
       
       
members = []

if args.users is not None:
    members = map(getDfbMember, args.users) 
else:
    members = getDfbMembers(None)

csvwriter = csv.writer(sys.stdout)
csvwriter.writerow(['User', 'Path', 'Visibility', 'URL'])

for member in members:
    if member["profile"]["status"] == "active":
        listSharedLinks(member["profile"]["email"], member["profile"]["member_id"], csvwriter)

