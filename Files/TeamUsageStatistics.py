from __future__ import print_function
import urllib
import urllib2
import json
import argparse
import sys
import csv
import time
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

parser = argparse.ArgumentParser(description='Lists advanced aggregate file stats of the DfB team.')
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
 
# Get a member's info (account details, quota usage)   
def getMemberInfo(memberId):
    request = urllib2.Request('https://api.dropboxapi.com/1/account/info')
    request.add_header("Authorization", "Bearer "+dfbToken)
    request.add_header("Content-type", 'application/json')
    request.add_header("X-Dropbox-Perform-As-Team-Member", memberId)
        
    try:
        return json.loads(urllib2.urlopen(request).read())
    except urllib2.HTTPError as error:
        print("   DfB ERROR: "+error.read())  

# Get all file metadata, counting files/folders/shares & noting last modification time
def countFiles(memberEmail, memberId, csvwriter):    
    
    lastModTime = None;
    files = Counter({'shared_folders':0, 'shared_files':0, 'shared_bytes':0, 'private_folders':0, 'private_files':0, 'private_bytes':0})
    cursor = None

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
                    
                    # Look for last time file was modified by the user (private file, or shared & modified by user)
                    if (shared == False) or (md["modifier"] is not None and md["modifier"]["email"] == memberEmail):
                        modTime = time.strptime(md["modified"][:-6], "%a, %d %b %Y %H:%M:%S")
                        if (lastModTime is None or modTime > lastModTime):
                            lastModTime = modTime

                    # Count the folder
                    if (md["is_dir"]):
                        if (shared):
                            files = files + Counter({'shared_folders':1})
                        else:
                            files = files + Counter({'private_folders':1})                    
                    # Count the file
                    else:
                        if (shared):
                            files = files + Counter({'shared_files':1, 'shared_bytes':md["bytes"]})
                        else:
                            files = files + Counter({'private_files':1, 'private_bytes':md["bytes"]})

            if response["reset"] and cursor is not None:
                sys.stderr.write("  ERROR: got a reset!")
                csvwriter.writerow([memberEmail, "/delta with cursor={!r} returned RESET".format(cursor), "ERROR", "-", "-", "-", "-", "-", "-", "-", "-"])
                break

            if not response['has_more']:
                break

            cursor = response['cursor']
        
        csvwriter.writerow([memberEmail, str(files["shared_bytes"]), formatSize(files["shared_bytes"]), str(files["shared_files"]), str(files["shared_folders"]), countSharedLinks(memberId),\
                           str(files["private_bytes"]), formatSize(files["private_bytes"]), str(files["private_files"]), str(files["private_folders"]), time.strftime('%Y-%m-%d %H:%M:%S', lastModTime)])
        
    except urllib2.HTTPError as error:
        print(error.read())
        csvwriter.writerow([memberEmail, "ERROR", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-"])
        sys.stderr.write("  ERROR: {}\n".format(error))
    

def countSharedLinks(memberId):
    cursor = None
    count = 0
    
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
            
    return count
            
            

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
csvwriter.writerow(['Email','Shared Bytes','Shared Size','Shared Files','Shared Folders','Shared Links','Private Bytes','Private Size','Private Files','Private Folders','Last File Mod Time'])

for member in members:
    if member["profile"]["status"] == "active":
        countFiles(member["profile"]["email"], member["profile"]["member_id"], csvwriter)
