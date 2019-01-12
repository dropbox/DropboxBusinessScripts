import urllib2
import json
import argparse
import csv
import sys

try:
    reload(sys)
    sys.setdefaultencoding('UTF8')
except NameError:
    pass  # Python 3 already defaults to utf-8

try:
    raw_input
except NameError:
    raw_input = input

parser = argparse.ArgumentParser(description='Lists members on a Dropbox for Business Team')
parser.add_argument( '-q', '--quota', action='store_const', const=True, default=False, dest='quota',
                     help='Include usage quota statistics - may increase script time to completion')
parser.add_argument( '-l', '--links', action='store_const', const=True, default=False, dest='links',
                     help='Include shared link count - may increase script time to completion')
parser.add_argument( '-f', '--folders', action='store_const', const=True, default=False, dest='folders',
                     help='Include shared folder count - may increase script time to completion')

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
    except urllib2.HTTPError as error:
        parser.error(error.read())
 
# Get a member's info (account details, quota usage)   
def getMemberInfo(memberId):
    request = urllib2.Request('https://api.dropboxapi.com/1/account/info')
    request.add_header("Authorization", "Bearer "+dfbToken)
    request.add_header("Content-type", 'application/json')
    request.add_header("X-Dropbox-Perform-As-Team-Member", memberId)
        
    try:
        return json.loads(urllib2.urlopen(request).read())
    except urllib2.HTTPError as error:
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
    except urllib2.HTTPError as error:
        parser.error(error.read())

# Get the count of shared links for the member
def countSharedLinks(memberId):
    cursor = None
    count = 0
    
    try:
        while True:    
            params = {}
            if cursor is not None:
                params['cursor'] = cursor
            request = urllib2.Request('https://api.dropboxapi.com/2/sharing/list_shared_links', json.dumps(params))
            request.add_header("Authorization", "Bearer "+dfbToken)
            request.add_header("Dropbox-API-Select-User", memberId)
            request.add_header("Content-Type", "application/json")
            response_string = urllib2.urlopen(request).read()
            response = json.loads(response_string)
            count = count + len(response["links"])
            if not response['has_more']:
                break
            cursor = response['cursor']
    except Exception as e:
        return "ERROR"
            
    return count

# Get the count of shared folders for the member
def countSharedFolders(memberId):
    cursor = None
    count = 0
    owner = 0
    
    try:
        while True:    
            params = {}
        
            url = 'https://api.dropboxapi.com/2/sharing/list_folders'
            if cursor is not None:
                params['cursor'] = cursor
                url = 'https://api.dropboxapi.com/2/sharing/list_folders/continue'
            
            request = urllib2.Request(url, json.dumps(params))
            request.add_header("Authorization", "Bearer "+dfbToken)
            request.add_header("Dropbox-API-Select-User", memberId)
            request.add_header("Content-Type", "application/json")
            response_string = urllib2.urlopen(request).read()
            response = json.loads(response_string)
            count = count + len(response["entries"])
            for entry in response["entries"]:
                if entry["access_type"][".tag"] == 'owner':
                    owner = owner + 1
    
            if not 'cursor' in response:
                break
            cursor = response['cursor']
    
    except Exception as e:
        return {"total":"ERROR", "owner":"ERROR", "member":"ERROR"}
                    
    return {"total":count, "owner":owner, "member":(count-owner)}

def formatSize(num, suffix='B'):
    for unit in ['','K','M','G','T','P','E','Z']:
        if abs(num) < 1000.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)
       

csvwriter = csv.writer(sys.stdout)

header = ['Email', 'First Name', 'Last Name', 'Status', 'Groups']

if args.quota:
    header = header + ['Locale', 'Normal Usage', 'Normal Usage (bytes)', 'Team Shared Usage', 'Team Shared Usage (bytes)']
if args.links:
    header = header + ['Shared Links']
if args.folders:
    header = header + ['Shared Folders (Total)', 'Shared Folders (Owner)', 'Shared Folders (Member)']

    
csvwriter.writerow(header)

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
    
    member_row = [member["profile"]["email"], \
                  member["profile"]["given_name"], \
                  member["profile"]["surname"], \
                  member["profile"]["status"],
                  groupstr]
    
    # Member info & quota
    if args.quota:
        if member["profile"]["status"] == "active":
            info = getMemberInfo(member["profile"]["member_id"])
            member_row = member_row + [info["locale"], \
                                       formatSize(info["quota_info"]["normal"]), \
                                       str(info["quota_info"]["normal"]), \
                                       formatSize(info["quota_info"]["shared"]), \
                                       str(info["quota_info"]["shared"])]
        else:
            member_row = member_row + ['-', '-', '-', '-', '-']
    
    # Shared links count
    if args.links:
        if member["profile"]["status"] == "active":
            member_row = member_row + [countSharedLinks(member["profile"]["member_id"])]
        else:
            member_row = member_row + ['-']

    # Shared folder count
    if args.folders:
        if member["profile"]["status"] == "active":
            shares = countSharedFolders(member["profile"]["member_id"])
            member_row = member_row + [shares["total"], shares["owner"], shares["member"]]
        else:
            member_row = member_row + ['-', '-', '-']

    csvwriter.writerow(member_row)
