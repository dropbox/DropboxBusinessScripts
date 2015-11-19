import urllib2
import json
import argparse
import sys
import csv

reload(sys)
sys.setdefaultencoding('UTF8')

parser = argparse.ArgumentParser(description='Lists all folders and folder permissions for groups in a DB or DE team.')
parser.add_argument('-g', '--group', dest='groups', action='append', help='Target group name to scan. All groups will '
                                                                          'be scanned be returned if unspecified. You '
                                                                          'may pass multiple -g arguments.')
args = parser.parse_args()

dfbToken = raw_input('Enter your Dropbox Business API App token (Team Member File Access permission): ')


# Get all DfB Groups
def get_groups():
    request = urllib2.Request('https://api.dropbox.com/1/team/groups/list', json.dumps({}))
    request.add_header("Authorization", "Bearer "+dfbToken)
    request.add_header("Content-type", 'application/json')
    try:
        response = json.loads(urllib2.urlopen(request).read())
        return response["groups"]
    # Exit on error here.  Probably bad OAuth token. Show DfB response.
    except urllib2.HTTPError, error:
        parser.error(error.read())


# Return member id of the first member that belongs to the specified group
def get_first_group_member(group_id):
    data = {"group_ids": [group_id]}
    request = urllib2.Request('https://api.dropbox.com/1/team/groups/get_info', json.dumps(data))
    request.add_header("Authorization", "Bearer "+dfbToken)
    request.add_header("Content-type", 'application/json')
    try:
        response = json.loads(urllib2.urlopen(request).read())
        return response["groups"][0]["members"][0]["profile"]["member_id"]
    except urllib2.HTTPError, error:
        parser.error(error.read())


# Find all folders in a particular group (by searching for a member & including unmounted folders)
# will also print groups that the first user found of the anchor group is a part of and flag them as checked
def get_group_folders(csv_writer, checked, anchor_group_id):

    checking = {anchor_group_id: []}

    try:
        request = urllib2.Request('https://api.dropbox.com/1/shared_folders'
                                  '?include_membership=true&show_unmounted=true')
        request.add_header("Authorization", "Bearer "+dfbToken)
        request.add_header("X-Dropbox-Perform-As-Team-Member", get_first_group_member(anchor_group_id))
        response_string = urllib2.urlopen(request).read()
        response = json.loads(response_string)

        # for all groups that each shared folder has access to, add line to print to each group's folders array
        for folder in response:
            # for each group that has access to a folder
            for folder_group in folder['groups']:
                folder_group_id = folder_group['group']['id']

                # verify that the group is in the list of currently active and inhabited groups
                # and the group hasn't already been checked/printed out
                if folder_group_id in checked and checked[folder_group_id] is False:

                    # if this group passes those but isn't already being tracked for this user,
                    # add it to our checking list
                    if folder_group_id not in checking:
                        checking[folder_group_id] = []

                    # log the folder in the list of folders this group has access to
                    checking[folder_group_id].append([
                        folder_group['group']['display_name'].encode("utf-8"),
                        folder_group['access_type'],
                        folder['shared_folder_id'],
                        folder["owner"]["display_name"],
                        folder['shared_folder_name'].encode("utf-8")
                    ])

    except urllib2.HTTPError as error:
        sys.stderr.write("  ERROR: {}\n".format(error))

    # flip the checked flag to true and print out folders by group
    for g in checking:
        checked[g] = True
        for f in checking[g]:
            csv_writer.writerow(f)

csv_writer = csv.writer(sys.stdout)
csv_writer.writerow(['Group Name', 'Group Access', 'Shared Folder Id', 'Shared Owner', 'Shared Folder Name'])

# find dfb groups
groups = get_groups()

# create a dictionary flagging if a group was checked from a previous group's first member
checkedGroups = dict()

# validate user entry of groups (if applicable) - either add just the specified groups as checking, else add all groups
if args.groups is not None:
    groupNames = dict()
    for group in groups:
        groupNames[group['group_name']] = group['group_id']

    for group in args.groups:
        if group not in groupNames:
            parser.error("Group " + group + " does not exist")
        else:
            checkedGroups[group['group_id']] = False
else:
    for group in groups:
        checkedGroups[group['group_id']] = False

# print folders for each group, so long as they have members and haven't been checked yet
for group in groups:
    if (args.groups is None or group["group_name"] in args.groups) and \
                    group["num_members"] > 0 and checkedGroups[group["group_id"]] is False:
            get_group_folders(csv_writer, checkedGroups, group["group_id"])
