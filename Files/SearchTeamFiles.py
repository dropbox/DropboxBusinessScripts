import urllib
import urllib2
import json
import argparse
import sys
import csv
from collections import Counter

reload(sys)
sys.setdefaultencoding('UTF8')

parser = argparse.ArgumentParser(description='Search for files in the DfB team.')
parser.add_argument('query', help='Search Query.')
parser.add_argument('-u', '--user', dest='users', action='append', help='Target user (email address) to scan.  All team members will be returned if unspecified. You may pass multiple -u arguments.')
parser.add_argument('-m', '--mode', default='filename_and_content', dest='mode', help='Search mode.  Valid options are filename_and_content, filename, or deleted_filename.')

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
    except urllib2.HTTPError, error:
        parser.error(error.read())


# Get all DfB members, paging through member list if necessary
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

# Searches a member's dropbox, paging through the results if necessary
def searchFiles(memberEmail, memberId, csvwriter):    
    cursor = None
    num_files = 0
    start = 0

    try:
        while True:
            params = {"start":start, "path":"", "mode":args.mode, "max_results":2, "query":args.query}
                
            request = urllib2.Request('https://api.dropbox.com/2/files/search', data=json.dumps(params))
            request.add_header("Authorization", "Bearer "+dfbToken)
            request.add_header("Dropbox-API-Select-User", memberId)
            request.add_header("Content-type", 'application/json')

            response_string = urllib2.urlopen(request).read()
            response = json.loads(response_string)

            for match in response["matches"]:
                metadata = match["metadata"]
                csvwriter.writerow([memberEmail, metadata["path_lower"], metadata[".tag"], match["match_type"][".tag"],\
                                     metadata["size"] if 'size' in metadata else '-', \
                                     formatSize(metadata["size"]) if 'size' in metadata else '-', \
                                     metadata["server_modified"] if 'server_modified' in metadata else '-'])
                num_files = num_files + 1

            start = response['start']

            if not response['more']:
                break
        
        sys.stderr.write("  found {} matches for {} \n".format(num_files, memberEmail))
        
    except urllib2.HTTPError as error:
        parser.error(error.read())


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

csvwriter.writerow(['User', 'Path', 'Type', 'Match Type', 'Size (bytes)', 'Size (formatted)', 'Modified'])

#TODO: Thread this?
for member in members:
    if member["profile"]["status"] == "active":
        files = searchFiles(member["profile"]["email"], member["profile"]["member_id"], csvwriter)
