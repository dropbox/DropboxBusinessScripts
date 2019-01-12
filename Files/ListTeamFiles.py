import urllib
import urllib2
import json
import argparse
import sys
import csv
from collections import Counter

try:
    reload(sys)
    sys.setdefaultencoding('UTF8')
except NameError:
    pass  # Python 3 already defaults to utf-8

try:
    raw_input
except NameError:
    raw_input = input

parser = argparse.ArgumentParser(description='Lists all files by user in the DfB team.')
parser.add_argument('-u', '--user', dest='users', action='append', help='Target user (email address) to scan.  All team members will be returned if unspecified. You may pass multiple -u arguments.')

args = parser.parse_args()

dfbToken = raw_input('Enter your Dropbox Business API App token (Team Member File Access permission): ')

#Look up a DfB member from an email address
def getDfbMember(email):
    request = urllib2.Request('https://api.dropbox.com/1/team/members/get_info', json.dumps({'email':email}))
    request.add_header("Authorization", "Bearer "+dfbToken)
    request.add_header("Content-type", 'application/json')
    try:
        return json.loads(urllib2.urlopen(request).read())
    
    # Exit on error here.  Probably user not found or bad OAuth token.  Show DfB response.
    except urllib2.HTTPError as error:
        parser.error(error.read());


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

# List a member's dropbox 
def listFiles(memberEmail, memberId, csvwriter):    
    cursor = None
    num_files = 0

    try:
        while True:
            params = {}
            if cursor is not None:
                params['cursor'] = cursor
            request = urllib2.Request('https://api.dropboxapi.com/1/delta', data=urllib.urlencode(params))
            request.add_header("Authorization", "Bearer "+dfbToken)
            request.add_header("X-Dropbox-Perform-As-Team-Member", memberId)

            response_string = urllib2.urlopen(request).read()
            response = json.loads(response_string)

            for path, md in response["entries"]:
                if md is None:
                    pass  # Delete entry.  Skip it.
                else:
                    
                    shared = False
                    if 'parent_shared_folder_id' in md or 'shared_folder' in md:
                        shared = True
                        
                    if md["is_dir"]:
                        csvwriter.writerow([memberEmail, md["path"].encode("utf-8"), "Folder", "-", "-", md["modified"], str(shared)])
                    else:
                        csvwriter.writerow([memberEmail, md["path"].encode("utf-8"), md["mime_type"], str(md["bytes"]), md["size"], md["modified"], str(shared)])
                    num_files += 1

            if response["reset"] and cursor is not None:
                sys.stderr.write("  ERROR: got a reset!")
                csvwriter.writerow([memberEmail, "/delta with cursor={!r} returned RESET".format(cursor), "ERROR", "-", "-", "-", "-"])
                break

            cursor = response['cursor']

            if not response['has_more']:
                break
        
        sys.stderr.write("  listed {} files/folders for {} \n".format(num_files, memberEmail))
        
        
    except urllib2.HTTPError as error:
        csvwriter.writerow([memberEmail, "/delta with cursor={!r} unknown error".format(cursor), "ERROR", "-", "-", "-", "-", "-"])
        sys.stderr.write("  ERROR: {}\n".format(error))


def formatSize(num, suffix='B'):
    for unit in ['','K','M','G','T','P','E','Z']:
        if abs(num) < 1000.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)
       
       
members = []
if (args.users is not None):
    members = map(getDfbMember, args.users) 
else:
    members = getDfbMembers(None)

csvwriter = csv.writer(sys.stdout)

csvwriter.writerow(['User', 'Path', 'Type', 'Size (bytes)', 'Size (formatted)', 'Modified', 'Shared'])

#TODO: Thread this?
for member in members:
    if member["profile"]["status"] == "active":
        files = listFiles(member["profile"]["email"], member["profile"]["member_id"], csvwriter)
