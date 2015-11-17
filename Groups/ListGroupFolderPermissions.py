import urllib
import urllib2
import json
import argparse
import sys
import csv
from collections import Counter

reload(sys)
sys.setdefaultencoding('UTF8')

parser = argparse.ArgumentParser(description='Lists all folders and folder permissions for groups in a DB or DE team.')
parser.add_argument('-g', '--group', dest='groups', action='append', help='Target group name to scan.  All groups will be scanned be returned if unspecified. You may pass multiple -g arguments.')
args = parser.parse_args()

dfbToken = raw_input('Enter your Dropbox Business API App token (Team Member File Access permission): ')

#Get all DfB Groups
def getDfBGroups():
    request = urllib2.Request('https://api.dropbox.com/1/team/groups/list', json.dumps({}))
    request.add_header("Authorization", "Bearer "+dfbToken)
    request.add_header("Content-type", 'application/json')
    try:
        response = json.loads(urllib2.urlopen(request).read())
        return response["groups"]
    # Exit on error here.  Probably bad OAuth token. Show DfB response.
    except urllib2.HTTPError, error:
        parser.error(error.read())


# Get the first member that belongs 
def getFirstGroupMember(groupId):
    data = {"group_ids":[groupId]}
    request = urllib2.Request('https://api.dropbox.com/1/team/groups/get_info', json.dumps(data))
    request.add_header("Authorization", "Bearer "+dfbToken)
    request.add_header("Content-type", 'application/json')
    try:
        response = json.loads(urllib2.urlopen(request).read())
        member = response["groups"][0]["members"][0]
        return member
    except urllib2.HTTPError, error:
        parser.error(error.read())

# Find all folders in a particular group (by searching for a member & including unmounted folders)
def findGroupFolders(memberId, groupId, csvwriter):
    try:
        request = urllib2.Request('https://api.dropbox.com/1/shared_folders?include_membership=true&show_unmounted=true')
        request.add_header("Authorization", "Bearer "+dfbToken)
        request.add_header("X-Dropbox-Perform-As-Team-Member", memberId)
        response_string = urllib2.urlopen(request).read()
        response = json.loads(response_string)

        for folder in response:
            if(len(folder['groups']) > 0):
                for group in folder['groups']:
                    if group['group']['id'] == groupId:
                        csvwriter.writerow([group['group']['display_name'].encode("utf-8"), group['access_type'],
                                            folder['shared_folder_id'], folder["owner"]["display_name"],
                                            folder['shared_folder_name'].encode("utf-8")])
                                            
    except urllib2.HTTPError as error:
        sys.stderr.write("  ERROR: {}\n".format(error))

# find dfb groups
groups = getDfBGroups()

# validate user entry of groups (if applicable)
if (args.groups is not None):
    groupNames = []
    for group in groups:    
        groupNames.append(group["group_name"])

    for group in args.groups:
        if group not in groupNames:
            parser.error("Group "+group+" does not exist")

csvwriter = csv.writer(sys.stdout)
csvwriter.writerow(['Group Name', 'Group Access', 'Shared Folder Id', 'Shared Owner', 'Shared Folder Name'])

# print folders for each group
for group in groups:
    if (args.groups is None) or (group["group_name"] in args.groups):
        if group["num_members"] > 0:
            member = getFirstGroupMember(group["group_id"])
            findGroupFolders(member["profile"]["member_id"], group["group_id"], csvwriter)
