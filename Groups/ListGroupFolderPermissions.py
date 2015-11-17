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

args = parser.parse_args()

dfbToken = raw_input('Enter your Dropbox Business API App token (Team Member File Access permission): ')

groupFolders = dict()

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


# Find all unique groups and group folder accesses
def findGroupFolders(memberEmail, memberId, csvwriter):

    try:

        request = urllib2.Request('https://api.dropbox.com/1/shared_folders?include_membership=true')
        request.add_header("Authorization", "Bearer "+dfbToken)
        request.add_header("X-Dropbox-Perform-As-Team-Member", memberId)

        response_string = urllib2.urlopen(request).read()
        response = json.loads(response_string)

        for folder in response:
            if(len(folder['groups']) > 0):
                for group in folder['groups']:

                    # if we encounter a new group, log new group
                    if group['group']['id'] not in groupFolders:
                        groupFolders['id'] = []

                    # if we encounter a new group folder permission, log new permission
                    if folder['shared_folder_id'] not in groupFolders['id']:
                        groupFolders['id'].append(folder['shared_folder_id'])
                        csvwriter.writerow([folder['shared_folder_id'], folder['shared_folder_name'].encode("utf-8"),
                            group['group']['id'], group['group']['display_name'].encode("utf-8"), group['access_type']])

    except urllib2.HTTPError as error:
        sys.stderr.write("  ERROR: {}\n".format(error))

# find all DfB members
members = getDfbMembers(None)
csvwriter = csv.writer(sys.stdout)
csvwriter.writerow(['Shared Folder Id', 'Shared Folder Name', 'Group Id', 'Group Name', 'Access'])

# find all group permissions for shared folders
for member in members:
    if member["profile"]["status"] == "active":
        findGroupFolders(member["profile"]["email"], member["profile"]["member_id"], csvwriter)