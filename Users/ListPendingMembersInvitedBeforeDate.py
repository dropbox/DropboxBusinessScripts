from __future__ import print_function
import urllib2
import json
import argparse
import sys
import time
import datetime

try:
    reload(sys)
    sys.setdefaultencoding('UTF8')
except NameError:
    pass  # Python 3 already defaults to utf-8

try:
    raw_input
except NameError:
    raw_input = input

parser = argparse.ArgumentParser(description='List pending members whom were invited prior to a specified date')
parser.add_argument('-d', '--date', dest='date', help='List members invited prior to this date (yyyy-mm-dd format)',required=True)
args = parser.parse_args()

# parse to utc datetime
utcdate = int(time.mktime(datetime.datetime.strptime(args.date, "%Y-%m-%d").timetuple())) * 1000

#ask for audit token
dfbAuditToken = raw_input('Enter your Dropbox Business API App token (Team Auditing permission): ')

# Get all DfB members, paging through results if necessary
def getDfbMembers(cursor):
    data = {"limit":100}
    
    if cursor is not None:
        data["cursor"] = cursor
    
    request = urllib2.Request('https://api.dropbox.com/1/team/members/list', json.dumps(data))
    request.add_header("Authorization", "Bearer "+dfbAuditToken)
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


# find invites before a certain date as UTC timestamp
def getInvitesBeforeDate(date, invites, cursor):
    data = { "category": "members", "limit": 1000, "end_ts": date }
    
    if cursor is not None:
        data["cursor"] = cursor

    request = urllib2.Request('https://api.dropbox.com/1/team/log/get_events', json.dumps(data))
    request.add_header("Authorization", "Bearer "+dfbAuditToken)
    request.add_header("Content-type", 'application/json')
    try:
        response = json.loads(urllib2.urlopen(request).read())
        for event in response['events']:
            if(event['event_type'] == 'member_invite'):
                invites[event['info_dict']['email']] = event

        if response["has_more"]:
            getInvitesBeforeDate(date, invites, cursor=response["cursor"])

    except urllib2.HTTPError as error:
        parser.error(error.read())

## To delete the pending invites, uncomment the following method & variable, and the commented section below.  Note that delete prompts for a member management API key ##
#dfbManagmentToken = None
#def removeMember(memberId):
#    global dfbManagmentToken
#    if dfbManagmentToken is None:
#       dfbManagmentToken = raw_input('Enter your Dropbox Business API App token (Member Management permission): ')
#    
#    data = {"member_id": memberId}
#    request = urllib2.Request('https://api.dropbox.com/1/team/members/remove', json.dumps(data))
#    request.add_header("Authorization", "Bearer "+dfbManagmentToken)
#    request.add_header("Content-type", 'application/json')
#    try:
#        response = json.loads(urllib2.urlopen(request).read())
#    except urllib2.HTTPError, error:
#        parser.error(error.read())
        

# find all invited members
invitedMembers = []
print("Getting invited members... ")
for member in getDfbMembers(None):
    if member['profile']['status'] == 'invited':
        invitedMembers.append(member['profile'])

# get all invite events before a particular date
print("Looking up invitation times...")
invites = dict()
getInvitesBeforeDate(utcdate, invites, None)

# figure out if there's overlap between invited users & old invitations
invitedBeforeDate = []
for member in invitedMembers:
    if member['email'] in invites:
        member['invited'] = invites[member['email']]['time'][0:10]
        invitedBeforeDate.append(member)

# sort by invitation date ascending
invitedBeforeDate.sort(key=lambda x: datetime.datetime.strptime(x['invited'], '%Y-%m-%d'))

print("-----------------------------------------------------------------------------------")
print("The following "+str(len(invitedBeforeDate)) +" out of "+ str(len(invitedMembers)) +" pending invitations were sent before " + str(args.date))
print("-----------------------------------------------------------------------------------")

for d in invitedBeforeDate:
    print(d['email']+" was invited on "+invites[d['email']]['time'][0:10])
    
    ## To delete the pending invites, uncomment the following section & the above removeMember method ##
    #confirm = raw_input('  Delete pending invite? Type "YES" to delete, or enter to continue without deleting: ')
    #if confirm == 'YES':
    #    removeMember(d['member_id'])
    #    print "  (deleted pending invitation to "+d['email']+")"
    #else:
    #    print "  (invite was not deleted)"