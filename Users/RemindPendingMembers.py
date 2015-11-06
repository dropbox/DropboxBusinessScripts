import urllib
import urllib2
import json
import argparse
import sys
from collections import Counter

reload(sys)
sys.setdefaultencoding('UTF8')

parser = argparse.ArgumentParser(description='Send reminder emails to all invited (but not joined) members.')

args = parser.parse_args()

dfbToken = raw_input('Enter your Dropbox Business API App token (Team Member Management permission): ')

# Get all DfB members, paging through member list if necessary
def getDfbMembers(cursor):    
    data = {"limit":100}
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

# Sends a reminder
def remind(memberId):    
    params = {'member_id':memberId}
    request = urllib2.Request('https://api.dropbox.com/1/team/members/send_welcome_email', data=json.dumps(params))
    request.add_header("Authorization", "Bearer "+dfbToken)
    request.add_header("Content-type", 'application/json')
    try:
        urllib2.urlopen(request).read()
    except urllib2.HTTPError, error:
        parser.error(error.read())


members = getDfbMembers(None)

print "Reminding invited members.."

for member in members:
    if member["profile"]["status"] == "invited":
        print "  reminding "+member["profile"]["email"]
        remind(member["profile"]["member_id"])

print "Done"
