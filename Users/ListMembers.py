import urllib2
import json
import argparse
import csv
import sys

reload(sys)
sys.setdefaultencoding('UTF8')

parser = argparse.ArgumentParser(description='Lists members on a Dropbox for Business Team')
parser.add_argument( '-q', '--quota', action='store_const', const=True, default=False, dest='quota',
                     help='Include usage quota statistics - may increase script time to completion')
args = parser.parse_args()

dfbToken = raw_input('Enter your Dropbox Business API App token (Team Member File Access permission): ')

# Get all DfB members, paging through results if necessary
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
 
# Get a member's info (account details, quota usage)   
def getMemberInfo(memberId):
    request = urllib2.Request('https://api.dropboxapi.com/1/account/info')
    request.add_header("Authorization", "Bearer "+dfbToken)
    request.add_header("Content-type", 'application/json')
    request.add_header("X-Dropbox-Perform-As-Team-Member", memberId)
        
    try:
        return json.loads(urllib2.urlopen(request).read())
    except urllib2.HTTPError, error:
        parser.error(error.read())

# Get a dict of groupid - group name
def getGroups():
    request = urllib2.Request('https://api.dropbox.com/1/team/groups/list', json.dumps({}))
    request.add_header("Authorization", "Bearer "+dfbToken)
    request.add_header("Content-type", 'application/json')

    try:
        ret = {}
        for group in json.loads(urllib2.urlopen(request).read())["groups"]:
            ret[group["group_id"]] = group["group_name"]
        return ret
    except urllib2.HTTPError, error:
        parser.error(error.read())


def formatSize(num, suffix='B'):
    for unit in ['','K','M','G','T','P','E','Z']:
        if abs(num) < 1000.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)
       

csvwriter = csv.writer(sys.stdout)

if args.quota:
    csvwriter.writerow(['Email', \
                    'First Name', \
                    'Last Name', \
                    'Status', \
                    'Locale', \
                    'Normal Usage', \
                    'Normal Usage (bytes)', \
                    'Team Shared Usage', \
                    'Team Shared Usage (bytes)',
                    'Groups'
                    ])
else:
    csvwriter.writerow(['Email', \
                    'First Name', \
                    'Last Name', \
                    'Status', \
                    'Locale', \
                    'Groups'
                    ])

groupMap = getGroups()

for member in getDfbMembers(None):

    # Get the group names from the ID array
    groupstr = ''
    if 'groups' in member["profile"]:
        for group in member["profile"]["groups"]:
            if group in groupMap:
                if groupstr != '':
                    groupstr = groupstr + ", "
                groupstr = groupstr + groupMap[group]
        
    # Active members have account info with more info
    if args.quota:

        if member["profile"]["status"] == "active":

            # The info lookup for space usage adds a little bit of time
            info = getMemberInfo(member["profile"]["member_id"])
            csvwriter.writerow([member["profile"]["email"], \
                                member["profile"]["given_name"], \
                                member["profile"]["surname"], \
                                member["profile"]["status"], \
                                info["locale"], \
                                formatSize(info["quota_info"]["normal"]), \
                                str(info["quota_info"]["normal"]), \
                                formatSize(info["quota_info"]["shared"]), \
                                str(info["quota_info"]["shared"]), \
                                groupstr
                               ])
        else:
            csvwriter.writerow([member["profile"]["email"], \
                                member["profile"]["given_name"], \
                                member["profile"]["surname"], \
                                member["profile"]["status"], \
                                "-", \
                                "-", \
                                "-", \
                                "-", \
                                "-" \
                               ])
    else:

        if member["profile"]["status"] == "active":

            # The info lookup for space usage adds a little bit of time
            info = getMemberInfo(member["profile"]["member_id"])
            csvwriter.writerow([member["profile"]["email"], \
                                member["profile"]["given_name"], \
                                member["profile"]["surname"], \
                                member["profile"]["status"], \
                                info["locale"], \
                                groupstr
                               ])
        else:
            csvwriter.writerow([member["profile"]["email"], \
                                member["profile"]["given_name"], \
                                member["profile"]["surname"], \
                                member["profile"]["status"], \
                                "-", \
                                "-" \
                               ])