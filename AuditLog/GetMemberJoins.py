import urllib2
import json
import argparse
import csv
import sys

reload(sys)
sys.setdefaultencoding('UTF8')

parser = argparse.ArgumentParser(description='Gets Member Join Dates from the Audit Log')
args = parser.parse_args()

dfbToken = raw_input('Enter your Dropbox Business API App token (Team Auditing permission): ')

# Get audit log events
def getEvents(event_category, cursor):
    data = {"limit":1000, "category":event_category}
    if cursor is not None:
        data["cursor"] = cursor
    
    request = urllib2.Request('https://api.dropbox.com/1/team/log/get_events', json.dumps(data))
    request.add_header("Authorization", "Bearer "+dfbToken)
    request.add_header("Content-type", 'application/json')
    try:
        response = json.loads(urllib2.urlopen(request).read())
        events = response["events"]
        if response["has_more"]:
            events = events + getEvents(event_category, cursor=response["cursor"])
        return events
    
    # Exit on error here.  Probably bad OAuth token. Show DfB response.
    except urllib2.HTTPError, error:
        parser.error(error.read())


# Print member_join events
csvwriter = csv.writer(sys.stdout)
csvwriter.writerow(['Email', 'Join Date'])
for event in getEvents("members", None):
    if (event["event_type"] == 'member_join'):
        csvwriter.writerow([event["email"], event["time"]])
        