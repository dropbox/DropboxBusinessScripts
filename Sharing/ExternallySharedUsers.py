from __future__ import print_function
# Lists external shared users

import urllib2
import json
import argparse
import sys
import re
import threading

try:
    reload(sys)
    sys.setdefaultencoding('UTF8')
except NameError:
    pass  # Python 3 already defaults to utf-8

try:
    raw_input
except NameError:
    raw_input = input

# Collect user input
parser = argparse.ArgumentParser(description='Identifies externally shared users')
parser.add_argument('-d', '--domain', dest='domains', action='append', required=False,
                    help='Target domains (i.e. acme.com in email@acme.com) to scan. If not indicated, will list all '
                         'external users. You may pass multiple -d arguments.')
args = parser.parse_args()
token = raw_input('Enter your Dropbox Business API App token (Team Member File access permission): ')


# Get all team members, paging through results if necessary
def get_team_members(cursor):

    data = {"limit": 100}

    if cursor is not None:
        data["cursor"] = cursor

    request = urllib2.Request('https://api.dropbox.com/1/team/members/list', json.dumps(data))
    request.add_header("Authorization", "Bearer " + token)
    request.add_header("Content-type", 'application/json')
    try:
        response = json.loads(urllib2.urlopen(request).read())
        members = response["members"]

        if response["has_more"]:
            members = members + get_team_members(cursor=response["cursor"])

        return members

    # Exit on error here.  Probably bad OAuth token. Show Dropbox response.
    except urllib2.HTTPError as error:
        parser.error(error.read())


# get membership of all shared folders. may be limited to certain domains
def get_shared_users(team_member_id, users, folders, domains):

    request = urllib2.Request('https://api.dropbox.com/1/shared_folders?include_membership=true&show_unmounted=true')
    request.add_header("Authorization", "Bearer " + token)
    request.add_header("X-Dropbox-Perform-As-Team-Member", team_member_id)

    try:

        # for each shared folder,
        for folder in json.loads(urllib2. urlopen(request).read()):

            # if we haven't logged that shared folder before
            if folder['shared_folder_id'] not in folders:

                folders.append(folder['shared_folder_id'])

                # for each member of the shared folder
                for folder_member in folder['membership']:

                    user_email = folder_member['user']['email']
                    domain = str(re.search("@[\w.]+", user_email).group()[1:]).lower()

                    # if they're an external member we haven't seen before and this user's domain is one we're checking
                    if folder_member['user']['same_team'] is False and user_email not in users and \
                            (len(domains) == 0 or domain in domains):

                        # add their email and domain
                        users[user_email] = domain

    # Exit on error here.  Probably bad OAuth token. Show DfB response.
    except urllib2.HTTPError as error:
        parser.error(error.read())


# helper function for threading
def worker(team_subset, users, folders, domains):

    # get all unique shared folder external members
    for m in team_subset:
        if m['profile']['status'] == 'active':
            get_shared_users(m['profile']['member_id'], users, folders, domains)

print('Getting all team members...')

# all members of a Dropbox team
team_members = get_team_members(None)

# keep track of shared folders and users we've already checked
shared_folders = []
shared_users = dict()
domains = []

if args.domains:
    for d in args.domains:
        domains.append(str(d).lower())

print('Finding externally shared users at ' + ('all domains' if len(domains) == 0 else str(', '.join(domains))) + '...')

# batches of team members to distribute in about 100 threads
batch_size = 1 if len(team_members) < 100 else len(team_members) / 100
threads = []
batches = 0

while len(team_members) > 0:

    # split the team_members into batches to run concurrently
    subset = team_members[:batch_size] if len(team_members) >= batch_size else team_members
    team_members = team_members[len(subset):]

    # run thread to find external shares for that subset of the team members
    t = threading.Thread(target=worker, args=(subset, shared_users, shared_folders, domains))
    threads.append(t)
    t.start()

# prevent main thread from continuing until all of the threads have finished
for t in threads:
    t.join()

# sort by domain, then by user
for u in sorted(shared_users.items(), key=lambda x: (x[1], x[0])):
    print(u[0])
