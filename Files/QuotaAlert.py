
from __future__ import print_function
from __future__ import division
import json
import argparse
import csv
from urllib2 import Request, urlopen, HTTPError
from multiprocessing.dummy import Pool as ThreadPool
import sys

try:
    reload(sys)
    sys.setdefaultencoding('UTF8')
except NameError:
    pass  # Python 3 already defaults to utf-8

try:
    raw_input
except NameError:
    raw_input = input

'''
QuotaAlert.py
Scan all members of a Dropbox team and report on which users are near,
or over, a given per-user quota
REQUIRES: Team member file access permission
'''
UNITS = {"MB": 1024 ** 2, "GB": 1024 ** 3, "TB": 1024 ** 4}

dbxApiV2 = None

parser = argparse.ArgumentParser(
    description='Checks team member disk usage and reports on users near, or over, quota')
parser.add_argument('-o', '--output', nargs='?', default=sys.stdout,
                    type=argparse.FileType('wb'),
                    help='path to output file for CSV generation, default: stdout')
parser.add_argument('-q', '--quota', nargs='?', default=1000, type=int,
                    help='quota to check usage against, in units given with -u, default:1TB')
parser.add_argument('-u', '--units', nargs='?', choices=['MB', 'GB', 'TB'],
                    default='GB', help='unit value for quota, must be one of MB, GB, TB, default: GB')
parser.add_argument('-w', '--warn', nargs='?', default=80, type=int,
                    help='warning threshold, as a percentage of the quota, default: 80')
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

    fileQuota = args.quota * UNITS[args.units]
    warnQuota = fileQuota * (args.warn / 100.0)

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

    log("Collecting quota information - this may take a while...")
    pool = ThreadPool(args.threads)
    members = pool.map(getQuotaUsage, activeMembers)
    pool.close()
    pool.join()

    # Determine which users are near, or beyond, the quota value provided
    log("Checking for quota violations...")
    alertMembers = []
    members.sort(key=lambda mbr: mbr.quotaUsed, reverse=True)
    for member in members:
        memberUsage = member.quotaUsed / UNITS["GB"]
        if member.quotaUsed >= fileQuota:
            member.quotaStatus = Quota.VIOLATION
            alertMembers.append(member)
            log("Member {} ({}) is over their quota by {:,.2f}GB! ({:,.2f}GB of {:,.2f}GB)"
                .format(
                        member.fullName, member.email,
                        (member.quotaUsed - fileQuota) / UNITS["GB"],
                        memberUsage, fileQuota / UNITS["GB"]
                        ))
        elif member.quotaUsed >= warnQuota:
            member.quotaStatus = Quota.WARN
            alertMembers.append(member)
            log("Member {} ({}) is above {}% of their max quota! ({:,.2f}GB of {:,.2f}GB)"
                .format(
                        member.fullName, member.email, args.warn, memberUsage,
                        fileQuota / UNITS["GB"]
                        ))

    # Write final output
    log("Processing complete, writing output to {}".format(args.output.name))
    dumpCsvFile(alertMembers)

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

def getQuotaUsage(member):
    """Get disk usage information for a Dropbox for Business team member"""
    try:
        usage = dbxApiV2.call("/users/get_space_usage", member.id)
        # Populate the member object with the usage info
        member.quotaUsed = usage["used"]
        member.quotaAllocated = usage["allocation"]["allocated"]
        member.quotaType = usage["allocation"][".tag"]
        member.teamQuotaUsed = usage["allocation"]["used"]
        return member
    except HTTPError as error:
        status = json.loads(error.read())
        if status["error"][".tag"] == "invalid_select_user":
            log("Failed to retrieve quota information for {} ({}), current status: {}"
                .format(member.fullName, member.email, member.status), True)
            member.quotaUsed = 0
            member.quotaAllocated = 0
            member.quotaType = 0
            member.teamQuotaUsed = 0
            return member

        parser.error(status)

def dumpCsvFile(members):
    """Write member information to a CSV file"""
    if args.output == sys.stdout:
        log("-------------------------- BEGIN CSV OUTPUT --------------------------")

    csvwriter = csv.writer(args.output)
    csvwriter.writerow(['First Name',
                        'Last Name',
                        'Email',
                        'Account Status',
                        'Quota Status',
                        'Quota Usage (bytes)',
                        ])
    for member in members:
        csvwriter.writerow([member.firstName,
                            member.lastName,
                            member.email,
                            member.status,
                            member.quotaStatus,
                            str(member.quotaUsed)
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
    log("Warning threshold set to {}%".format(args.warn))
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

class Quota:
    """Enum for Quota status constants"""
    NORMAL = "NORMAL"
    WARN = "WARN"
    VIOLATION = "VIOLATION"

if __name__ == '__main__':
    main()
