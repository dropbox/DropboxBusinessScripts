# Lists all device sessions

import urllib2
import json
import argparse
import sys
import datetime
import dateutil.parser
import csv

reload(sys)
sys.setdefaultencoding('UTF8')
csv_writer = csv.writer(sys.stdout)

# Collect user input
parser = argparse.ArgumentParser(description='Lists all linked devices / sessions in the Dropbox Business team. If '
                                             'web/mobile/desktop is not specified, all device sessions will be listed.')
parser.add_argument('-u', '--user', dest='users', action='append',
                    help='Target users (email address) to scan. All team members will be scanned if unspecified. '
                         'You may pass multiple -u arguments.')
parser.add_argument('-w', '--web', dest='web', action='store_true', default=False,
                    help='Show web sessions.')
parser.add_argument('-d', '--desktop', dest='desktop', action='store_true', default=False,
                    help='Show desktop sessions.')
parser.add_argument('-m', '--mobile', dest='mobile', action='store_true', default=False,
                    help='Show mobile sessions.')
parser.add_argument('-b', '--before', dest='date',
                    help='List all device sessions connected before this date (yyyy-mm-dd format).  '
                         'All will be returned if unspecified.')

args = parser.parse_args()

# Get all types if none specified
if not args.web and not args.desktop and not args.mobile:
    args.web = args.desktop = args.mobile = True

before_date = None
if args.date:
    before_date = datetime.datetime.strptime(args.date, "%Y-%m-%d")

token = raw_input('Enter your Dropbox Business API App token (Team Member File Access permission): ')


# Look up a team member from a tag/value combination, where tags can be 'email', 'team_member_id', or 'external_id'
def get_dfb_member(tag, value):
    request = urllib2.Request('https://api.dropbox.com/2/team/members/get_info',
                              json.dumps({ 'members': [{'.tag': tag, tag: value}]}))
    request.add_header("Authorization", "Bearer "+token)
    request.add_header("Content-type", 'application/json')

    try:
        response = json.loads(urllib2.urlopen(request).read())
        if 'id_not_found' in response[0]:
            parser.error("Member "+value+" is not on the team")
        return response[0]

    # Exit on error here.  Probably user not found or bad OAuth token.  Show response.
    except urllib2.HTTPError, error:
        parser.error(error.read())


# Get a member's sessions that match the input date & type arguments
def get_member_sessions(email):
    member_id = get_dfb_member('email', email)['profile']['team_member_id']
    data = { 'include_web_sessions':args.web, 'include_desktop_clients':args.desktop,
             'include_mobile_clients': args.mobile, 'team_member_id': member_id}
    request = urllib2.Request('https://api.dropboxapi.com/2/team/devices/list_member_devices', json.dumps(data))
    request.add_header("Authorization", "Bearer "+token)
    request.add_header("Content-type", 'application/json')

    try:
        response = json.loads(urllib2.urlopen(request).read())
        return list_sessions(member_id, email, response, False)
    except urllib2.HTTPError, error:
        parser.error(error.read())


# Get a team's sessions that match the input date & type arguments
def get_team_sessions(cursor):

    data = {
        'include_web_sessions': args.web,
        'include_desktop_clients': args.desktop,
        'include_mobile_clients': args.mobile
    }

    if cursor is not None:
        data["cursor"] = cursor

    request = urllib2.Request('https://api.dropboxapi.com/2/team/devices/list_team_devices', json.dumps(data))
    request.add_header("Authorization", "Bearer "+token)
    request.add_header("Content-type", 'application/json')

    try:
        response = json.loads(urllib2.urlopen(request).read())
        
        returned_sessions = [] 
        for d in response["devices"]:
            returned_sessions = returned_sessions + list_sessions(d['team_member_id'], None, d, True)
        if response["has_more"]:
            returned_sessions = returned_sessions + get_team_sessions(cursor=response["cursor"])
        return returned_sessions
    except urllib2.HTTPError, error:
        parser.error(error.read())


# Output sessions matching the date/type arguments specified them, then return them 
def list_sessions(member_id, member_email, sessions, all_team):

    # Look up member email, if we don't have it
    if member_email is None:
        member_email = get_dfb_member('team_member_id',member_id)['profile']['email']

    returned_sessions = []

    # Desktop sessions
    key = 'desktop_clients' if all_team else 'desktop_client_sessions'
    if key in sessions:
        for s in sessions[key]:
            if show_session(s):
                if 'created' not in s:
                    s['created'] = ''
                csv_writer.writerow(['Desktop', s['created'], member_email, s['platform'] + ' ' + s['host_name']])
                returned_sessions.append({'.tag': 'desktop_client', 'session_id': s['session_id'],
                                          'team_member_id': member_id, 'delete_on_unlink': True})

    # Mobile sessions
    key = 'mobile_clients' if all_team else 'mobile_client_sessions'    
    if key in sessions:
        for s in sessions[key]:
            if show_session(s):
                if 'created' not in s:
                    s['created'] = ''
                csv_writer.writerow(['Mobile', s['created'], member_email, s['device_name']])
                returned_sessions.append({'.tag': 'mobile_client', 'session_id': s['session_id'],
                                          'team_member_id': member_id })

    # Web sessions
    key = 'web_sessions' if all_team else 'active_web_sessions'
    if key in sessions:
        for s in sessions[key]:
            if show_session(s):
                if 'created' not in s:
                    s['created'] = ''
                csv_writer.writerow(['Web', s['created'], member_email, s['os'] + ' - ' + s['browser']])
                returned_sessions.append({'.tag': 'web_session', 'session_id': s['session_id'],
                                          'team_member_id': member_id})

    return returned_sessions


# Returns true if a session should be shown, per the args. Session type (desktop/web/mobile) is filtered in the API call
def show_session(session):
    if before_date is None:
        return True
    else:
        return 'created' in session and dateutil.parser.parse(session['created']).replace(tzinfo=None) < before_date


# Revoke a list of sessions
def deactivate_sessions(sessions):
    request = urllib2.Request('https://api.dropboxapi.com/2/team/devices/revoke_device_session_batch',
                              json.dumps({'revoke_devices': sessions}))
    request.add_header("Authorization", "Bearer "+token)
    request.add_header("Content-type", 'application/json')
    try:
        json.loads(urllib2.urlopen(request).read())
        print 'Deactivated ' + str(len(sessions)) + ' session(s).'
    except urllib2.HTTPError, error:
        parser.error(error.read())

csv_writer.writerow(['Platform', 'Created Date', 'Owner', 'Device'])

sessions = []

# List device sessions for specified users if specified
if args.users is not None:
    for u in args.users:
        sessions = sessions + get_member_sessions(u)
# Else the whole team
else:
    sessions = get_team_sessions(None)

# Uncomment to prompt to deactivate listed sessions ##
# if raw_input("Deactivate sessions? Type 'YES' to confirm. ") == "YES":
#    deactivate_sessions(sessions)
# else:
#    print "Skipping deactivation"

