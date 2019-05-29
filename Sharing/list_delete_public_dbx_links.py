'''This script will either list or delete all publically 
accessible shared links which do not have a password'''

import dropbox

def getmembers():
    '''get all member id's on a team'''

    # if team is > 1000, also use members/list/continue
    members = dbxt.team_members_list().members
    membersinfo = [(member.profile.team_member_id, member.profile.email)
                   for member in members]

    return membersinfo

def getlinks(userid):
    '''get all public links for an individual member'''

    links = dbxt.as_user(userid).sharing_list_shared_links().links
    linkurls = [link for link in links
                if link.link_permissions.resolved_visibility.is_public()]

    return linkurls

# def dellinks(userid):
#     '''delete all public links for an individual member'''

#     for link in getlinks(userid):
#         dbxt.as_user(userid).sharing_revoke_shared_link(link.url)
#         print("     %s has been deleted " % link.url)

# def delall():
#     '''delete all public links for all members'''

#     for (memberid, email) in getmembers():
#         dellinks(memberid)

def listlinks():
    '''print all public links urls for all members'''

    for (memberid, email) in getmembers():
        links = getlinks(memberid)
        link_count = len(links)
        print("Public Links: %s User: %s" % (link_count, email))
        for link in links:
            print("    %s" % link.url)

if __name__ == '__main__':
    print("This script requires a API token with 'Team Member File Access premissions'")
    token = (input("Enter your token: "))
    mode = (input("Enter a mode (either 'list' or 'delete'): "))

    dbxt = dropbox.DropboxTeam(token)

    if mode == "list":
        listlinks()

    ## CAUTION: Enabling this mode will allow deletion of unprotected shared links
    ## This could result in disruption to your team
    # elif mode == "delete":
    #     delall()

    else:
        print("Please enter a mode of list or delete")



