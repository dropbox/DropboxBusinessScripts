
from __future__ import print_function
from __future__ import division
import json
import argparse
import csv
from urllib2 import Request, urlopen, HTTPError
from multiprocessing.dummy import Pool as ThreadPool
import sys
reload(sys)
sys.setdefaultencoding('UTF8')  # @UndefinedVariable

'''
FileSizeQuotaAlert.py
Scan all members of a Dropbox team and report files that are at or over a given
quota value
REQUIRES: Team member file access permission
'''
UNITS = {"MB": 1024 ** 2, "GB": 1024 ** 3, "TB": 1024 ** 4}

dbxApiV2 = None
fileQuota = None

parser = argparse.ArgumentParser(
    description='Checks team member disk usage and reports on files that exceed a given quota')
parser.add_argument('-o', '--output', nargs='?', default=sys.stdout,
                    type=argparse.FileType('wb'),
                    help='path to output file for CSV generation, default: stdout')
parser.add_argument('-q', '--quota', nargs='?', default=1, type=int,
                    help='file quota to check usage against, in units given with -u, default:1TB')
parser.add_argument('-u', '--units', nargs='?', choices=['MB', 'GB', 'TB'],
                    default='GB', help='unit value for quota, must be one of MB, GB, TB, default: GB')
parser.add_argument("-l", "--limit", nargs='?', default=1000, type=int,
                    help='limit max records returned per Dropbox API call, default: 1000')
parser.add_argument("-t", "--threads", nargs='?', default=4, type=int,
                    help="worker thread count, default: 4")
parser.add_argument("-v", "--verbose", action="store_const",
                    default=False, const=True, help='enable verbose output')
args = parser.parse_args()

def main():
    dfbToken = raw_input('Enter your Dropbox Business API App token (Team Member File Access permission): ')

    if args.verbose:
        dumpArguments()

    global fileQuota
    fileQuota = args.quota * UNITS[args.units]

    log("Creating Dropbox V2 API Client")
    global dbxApiV2
    dbxApiV2 = DbxApi(DbxApi.DBX_API_V2, dfbToken)

    log("Collecting Member List...")
    members = getDfbMembers(None)
    # Filter out invited members as they can't consume any quota yet
    activeMembers = [member for member in members if member.status != "invited"]
    log("Got {} total team members ({} active, {} suspended, {} invited)"
        .format(
                len(members), len(activeMembers),
                len(getMemberSublist(members, "suspended")),
                len(getMemberSublist(members, "invited"))
                ))

    log("Collecting file quota information - this may take a while...")
    pool = ThreadPool(args.threads)
    members = pool.map(getFileQuotaUsage, activeMembers)
    pool.close()
    pool.join()

    # Write final output
    log("Processing complete, writing output to {}".format(args.output.name))
    dumpCsvFile(members)
    
def getDfbMembers(cursor):
    """Get a list of all Dropbox for Business team members"""
    if cursor is not None:
        data = {"cursor": cursor}
        endpoint = "/team/members/list/continue"
    else:
        data = {"limit": args.limit}
        endpoint = "/team/members/list"

    try:
        result = dbxApiV2.call(endpoint, None, json.dumps(data))
        members = listToMemberObj(result["members"])

        # Check to see if we got all team members, if not, get the rest
        if result["has_more"]:
            members = members + getDfbMembers(result["cursor"])

        return members
    except HTTPError as error:
        parser.error(error.read())

def getFileQuotaUsage(member):
    """Get file size information for a Dropbox for Business team member"""
    try:
        data = {"path": "", "recursive": True}
        response = dbxApiV2.call("/files/list_folder", member.id, json.dumps(data))
        fileData = response["entries"]
        member.files.extend(getFileQuotaViolations(fileData))
        hasMore = response["has_more"]
        while hasMore:
            data = {"cursor": response["cursor"]}
            response = dbxApiV2.call("/files/list_folder/continue", member.id, json.dumps(data))
            fileData = response["entries"]
            member.files.extend(getFileQuotaViolations(fileData))
            hasMore = response["has_more"]
        return member
    except HTTPError as httpError:
        # catch server errors and retry that user
        if 500 <= httpError.code <= 599: # Server error codes 500-599
            log("Encountered server error ({}) for user {}, retrying..."
                .format(httpError,member.fullName), True)
            # clear existing file quota info for user, and retry file quota request
            del member.files[:]
            return getFileQuotaUsage(member)
        elif 400 <= httpError.code <= 499: # Client error codes 400-499
            errStr = httpError.read()
            log("Client error for user {} (Status: {}): Error {}:{}"
                    .format(member.fullName, member.status, httpError.code, errStr), True)
            return None

def getFileQuotaViolations(files):
    violations = []
    for f in files:
        if f[".tag"] != "file": # skip folders
            continue
        if f["size"] >= fileQuota:
            violations.append(File(f))
    return violations
        
def dumpCsvFile(members):
    """Write member information to a CSV file"""
    if args.output == sys.stdout:
        log("-------------------------- BEGIN CSV OUTPUT --------------------------")

    csvwriter = csv.writer(args.output)
    csvwriter.writerow(['First Name',
                        'Last Name',
                        'Email',
                        'File Name',
                        'File Path',
                        'File Size (bytes)',
                        ])
    for member in members:
        if member is not None and len(member.files) > 0:
            for f in member.files:
                csvwriter.writerow([member.firstName,
                                    member.lastName,
                                    member.email,
                                    f.name,
                                    f.path,
                                    str(f.size)
                                    ])

def listToMemberObj(memberList):
    """Convert a list of member info dicts into a list of Member Class objects"""
    members = []
    for member in memberList:
        members.append(Member(member))
    return members

def getMemberSublist(members, status):
    sublist = []
    for member in members:
        if member.status == status:
            sublist.append(member)
    return sublist

def log(msg, isError=False):
    """Log information to stdout, or stderr based upon global verbosity setting"""
    if isError:
        print(msg, file=sys.stderr)
        return
    if args.verbose:
        print(msg)

def dumpArguments():
    log("Verbose output enabled")
    log("Output file set to {}".format(args.output.name))
    log("Quota set to {}{}".format(args.quota, args.units))
    log("Max records set to {}".format(args.limit))
    log("Worker threads set to {}".format(args.threads))

class DbxApi:
    """DbxApi - Convenience wrapper class around Dropbox API calls"""
    DBX_API_V1 = "https://api.dropbox.com/1"
    DBX_API_V2 = "https://api.dropboxapi.com/2"

    def __init__(self, baseUrl, accessToken):
        self.baseUrl = baseUrl
        self.accessToken = accessToken

    def call(self, endpoint, mbrId=None, payload=None, setContent=True):
        if payload is not None:
            payload = payload.encode('utf8')
            request = Request(self.baseUrl + endpoint, payload)
            request.add_header("Content-type", 'application/json')
        else:
            request = Request(self.baseUrl + endpoint)
        request.add_header("Authorization", "Bearer " + self.accessToken)
        request.get_method = lambda: 'POST'

        if mbrId is not None:
            if self.baseUrl == self.DBX_API_V2:
                request.add_header("Dropbox-API-Select-User", mbrId)
            else:
                request.add_header("X-Dropbox-Perform-As-Team-Member", mbrId)

        try:
            return json.loads(urlopen(request).read())
        except HTTPError:
            # raise exception to caller.
            raise

class Member:
    """Member - Convenience wrapper class around a Dropbox for Business team member"""
    def __init__(self, member):
        self.firstName = member["profile"]["name"]["given_name"]
        self.lastName = member["profile"]["name"]["surname"]
        self.fullName = self.firstName + " " + self.lastName
        self.id = member["profile"]["team_member_id"]
        self.email = member["profile"]["email"]
        self.status = member["profile"]["status"][".tag"]
        self.quotaStatus = Quota.NORMAL
        # Quota values won't be present until getQuotaUsage() is called!
        self.quotaUsed = None
        self.quotaAllocated = None
        self.quotaType = None
        self.teamQuotaUsed = None
        self.files = []

class File:
    """Member - Convenience wrapper class around file metadata"""
    def __init__(self, f):
        self.id = f["id"]
        self.name = f["name"]
        self.path = f["path_display"]
        self.size = f["size"]
        self.rev = f["rev"]
        

class Quota:
    """Enum for Quota status constants"""
    NORMAL = "NORMAL"
    WARN = "WARN"
    VIOLATION = "VIOLATION"

if __name__ == '__main__':
    main()
