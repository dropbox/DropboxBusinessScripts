# Lists all of the apps that team members have linked

import urllib2
import json
import argparse
import sys
import csv

reload(sys)
sys.setdefaultencoding('UTF8')

# Collect user input
parser = argparse.ArgumentParser(description='Lists all of the apps that team members have linked.')
parser.add_argument('-u', '--user', dest='users', action='append',
                    help='Target users (email address) to scan. All team members will be scanned if unspecified. '
                         'You may pass multiple -u arguments.')

args = parser.parse_args()

token = raw_input('Enter your Dropbox Business API App token (Team Member File access permission): ')


# Look up a team member from a tag/value combination, where tags can be 'email', 'team_member_id', or 'external_id'
def get_team_member(tag, value):

    data = {'members': [{'.tag': tag, tag: value}]}

    request = urllib2.Request('https://api.dropbox.com/2/team/members/get_info', json.dumps(data))
    request.add_header("Authorization", "Bearer " + token)
    request.add_header("Content-type", 'application/json')

    try:
        response = json.loads(urllib2.urlopen(request).read())
        return response[0] if len(response) > 0 else None

    # Exit on error here.  Probably user not found or bad OAuth token.  Show Dropbox response.
    except urllib2.HTTPError, error:
        parser.error(error.read())


# Get all team members, paging through results if necessary
def get_team(cursor):

    data = {}
    endpoint = ''

    if cursor is not None:
        data["cursor"] = cursor
        endpoint = '/continue'

    request = urllib2.Request('https://api.dropbox.com/2/team/members/list' + endpoint, json.dumps(data))
    request.add_header("Authorization", "Bearer " + token)
    request.add_header("Content-type", 'application/json')
    try:
        response = json.loads(urllib2.urlopen(request).read())
        members = response["members"]

        if response["has_more"]:
            members = members + get_team(cursor=response["cursor"])

        return members

    # Exit on error here.  Probably bad OAuth token. Show Dropbox response.
    except urllib2.HTTPError, error:
        parser.error(error.read())


# Get all linked apps for the specified member
def get_member_linked_apps(email):

    data = {'team_member_id': get_team_member('email', email)['profile']['team_member_id']}

    request = urllib2.Request('https://api.dropboxapi.com/2/team/linked_apps/list_member_linked_apps', json.dumps(data))
    request.add_header("Authorization", "Bearer " + token)
    request.add_header("Content-type", 'application/json')

    try:
        return json.loads(urllib2.urlopen(request).read())['linked_api_apps']

    # Exit on error here.  Probably user not found or bad OAuth token.  Show Dropbox response.
    except urllib2.HTTPError, error:
        parser.error(error.read())


# Get all linked apps for each member of the team
def get_team_linked_apps(cursor):

    data = {}

    if cursor is not None:
        data["cursor"] = cursor

    request = urllib2.Request('https://api.dropboxapi.com/2/team/linked_apps/list_team_linked_apps', json.dumps(data))
    request.add_header("Authorization", "Bearer " + token)
    request.add_header("Content-type", 'application/json')

    try:
        response = json.loads(urllib2.urlopen(request).read())
        apps = response['apps']

        if response["has_more"]:
            apps = apps + get_team_linked_apps(cursor=response["cursor"])

        return apps

    # Exit on error here.  Probably user not found or bad OAuth token.  Show Dropbox response.
    except urllib2.HTTPError, error:
        parser.error(error.read())


# takes in the list of apps and who's using them and then adds the current user's list of apps to that
def log_apps(user_email, user_apps, team_apps):

    # for each app a user has linked
    for a in user_apps:

        # if we haven't seen this app before, add it to the list of team apps
        if a['app_id'] not in team_apps:

            publisher = a['publisher'] if 'publisher' in a else ''
            name = a['app_name'] if 'app_name' in a else ''

            team_apps[a['app_id']] = {'app_name': name, 'publisher': publisher, 'users': []}

        # add the user's email to the list of people who use this app
        team_apps[a['app_id']]['users'].append(user_email)


csv_writer = csv.writer(sys.stdout)
csv_writer.writerow(['App', 'Publisher', '# of Users', 'Users'])

# apps, where each object is app_id: { id, name, users }
team_apps = dict()

# Log linked apps for specified users, else log apps for entire team
if args.users is not None:

    # for all users, get their apps and add it to the list of apps that the specified user(s) are using
    for u in args.users:
        log_apps(u, get_member_linked_apps(u), team_apps)

else:

    # get list of all team members and convert to dict of k=member_id, v=email
    team_emails = dict()

    for t in get_team(None):
        team_emails[t['profile']['team_member_id']] = t['profile']['email']

    # for each of the members of the team, if they've linked apps, log these to the list of team apps
    for a in get_team_linked_apps(None):
        if len(a['linked_api_apps']) > 0:
            log_apps(team_emails[a['team_member_id']], a['linked_api_apps'], team_apps)

app_names = dict()

# get the list of apps that we've run across and create a list of ids and number of users. *-1 makes it sort descending
for k in team_apps:
    app_names[k] = -1*len(team_apps[k]['users'])

# for each app in the list sorted by number of users, print it
for key in sorted(app_names, key=app_names.get):
    app = team_apps[key]
    csv_writer.writerow([app['app_name'], app['publisher'], len(app['users']), ', '.join(app['users'])])
