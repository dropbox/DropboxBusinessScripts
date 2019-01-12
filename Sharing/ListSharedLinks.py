# Lists all active shared links

import urllib2
import json
import argparse
import sys
import csv

try:
    reload(sys)
    sys.setdefaultencoding('UTF8')
except NameError:
    pass  # Python 3 already defaults to utf-8

try:
    raw_input
except NameError:
    raw_input = input

parser = argparse.ArgumentParser(description='Lists all files by user in the DfB team.')
parser.add_argument('-u', '--user', dest='users', action='append',
                    help='Target user (email address) to scan.  All team members will be returned if unspecified. '
                         'You may pass multiple -u arguments.')
parser.add_argument( '-p', '--public', action='store_const', const=True, default=False, dest='public',
                     help='Show unprotected public links only - won\'t list team only or password protected links' )

args = parser.parse_args()

dfbToken = raw_input('Enter your Dropbox Business API App token (Team Member File Access permission): ')


#Look up a DfB member from an email address
def getDfbMember(emails):

    members = []

    for e in emails:
        members.append({".tag": "email", "email": e})

    data = {"members": members}

    request = urllib2.Request('https://api.dropboxapi.com/2/team/members/get_info', json.dumps(data))
    request.add_header("Authorization", "Bearer "+dfbToken)
    request.add_header("Content-type", 'application/json')
    try:
        return json.loads(urllib2.urlopen(request).read())
    
    # Exit on error here.  Probably user not found or bad OAuth token.  Show DfB response.
    except urllib2.HTTPError as error:
        parser.error(error.read())


# Get all DfB members, paging through results if necessary
def getDfbMembers(cursor):

    data = {}
    endpoint = ''

    if cursor is not None:
        data = {
            "cursor": cursor
        }
        endpoint = 'https://api.dropboxapi.com/2/team/members/list/continue'
    else:
        data = {
            "limit": 100,
            "include_removed": False
        }
        endpoint = 'https://api.dropboxapi.com/2/team/members/list'
    
    request = urllib2.Request(endpoint, json.dumps(data))
    request.add_header("Authorization", "Bearer "+dfbToken)
    request.add_header("Content-type", 'application/json')
    try:
        response = json.loads(urllib2.urlopen(request).read())
        members = response["members"]
        
        if response["has_more"]:
            members = members + getDfbMembers(cursor=response["cursor"])

        return members
    
    # Exit on error here.  Probably bad OAuth token. Show DfB response.
    except urllib2.HTTPError as error:
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
            if (args.public is False) or (args.public is True and link['visibility']['.tag'] == 'public'):
                csvwriter.writerow([memberEmail, link['path'] if 'path' in link else '', link['visibility']['.tag'],
                                    link['url']])
        
    except urllib2.HTTPError as error:
        csvwriter.writerow([memberEmail, error, "ERROR", memberId])
        sys.stderr.write("  ERROR: {}\n".format(error))

csvwriter = csv.writer(sys.stdout)
csvwriter.writerow(['User', 'Path', 'Visibility', 'URL'])
       
members = []

if args.users is not None:
    members = getDfbMember(args.users)
else:
    members = getDfbMembers(None)

for member in members:
    if member["profile"]["status"][".tag"] == "active":
        listSharedLinks(member["profile"]["email"], member["profile"]["team_member_id"], csvwriter)

