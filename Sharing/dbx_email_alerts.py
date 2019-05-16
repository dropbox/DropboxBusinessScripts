#install the dropbox SDK with 'pip install dropbox'
import dropbox
import datetime
import time
import smtplib
import requests

token = "<enter token here>"
cursor = None

# instantiating dropbox team object
dbxt = dropbox.DropboxTeam(token)

# Full list of alerts available at:
# https://www.dropbox.com/developers/documentation/http/teams#team_log-get_events
alerts = ["sign_in_as_session_start",
          "member_change_admin_role",
          "shared_link_create",
          # "login_fail",
          # "shared_folder_create",
          # "file_request_create",
          # "account_capture_relinquish_account",
          # "shared_content_copy"
          ]

# If using gmail, "enable less secure apps" needs to be turned on.
# For a more robust solution, use an email API tool e.g. Mailgun
sender_email = "<sender_email@gmail.com>"
sender_pw = "<sender_password"
receiver_email = "<receiver_email>"

def send_email(subject, body):
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()
    s.login(sender_email, sender_pw)
    message = "Subject: %s \n\n %s" % (subject, body)
    s.sendmail(sender_email, receiver_email, message)
    s.quit()

def check_alerts(token):
    global cursor

    #On the first cycle, the cursor will be none. The cursor will be
    #updated on following cycles
    if cursor is None:

        # Start time has an offset of 1 minute from the current time. Can
        # optionally increase or decrease the start time offset. For example,
        # if you stop the script and plan to restart it 12 hours later, you may
        # want to increase the offset to 12 hours so that events in the 12 hours
        # prior to start are captured.
        start_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
        time_range = dropbox.team_common.TimeRange(start_time=start_time)

        log = dbxt.team_log_get_events(time=time_range)
        events = log.events
        cursor = log.cursor

        for event in events:
            if event.event_type._tag in alerts:
                email_subject = event.event_type._tag
                email_body = "Event was found at: %s" % event.timestamp
                send_email(email_subject, email_body)

    else:
        log = dbxt.team_log_get_events_continue(cursor)
        events = log.events
        cursor = log.cursor
        has_more = log.has_more

        for event in events:
            if event.event_type._tag in alerts:
                email_subject = event.event_type._tag
                email_body = "Event was found at: %s" % event.timestamp
                send_email(email_subject, email_body)

# run the check alerts sequence on a 1 minute loop.
while True:
    try:
        print(datetime.datetime.utcnow())
        check_alerts(token)
        time.sleep(60)

    except requests.exceptions.ReadTimeout:
        print ("Request Timeout")

    except requests.exceptions.ConnectionError:
        print ("Connection Error")

    # Breaking on other errors and notifying of a required restart.
    # It is recommended to handle potential Dropbox and other
    # errors specifically
    except Exception as e:
        print(e)
        subject = "Alert Service Error - Restart Required"
        body = "Alert service ecountered an error and needs to be restarted: %s" % e
        send_email(subject, body)
        break
