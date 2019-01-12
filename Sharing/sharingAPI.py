from __future__ import print_function

import json
import requests

def create_shared_folder(token, creator, path):
	url = 'https://api.dropboxapi.com/1/shared_folders/'
	headers = {'Authorization': 'Bearer %s' % token, 'X-Dropbox-Perform-As-Team-Member': creator}
	params = {'path': path}

	r = requests.post(url, headers=headers, params=params)

	if r.status_code == 200:
		return r.json()['shared_folder_id']
	else:
		print('HTTP error %s (%s - %s)' % (r.status_code, r.reason, r.text))
		return False

def invite_to_shared_folder(token, inviter, invitee, invitee_role, folder_id):
	url = 'https://api.dropboxapi.com/1/shared_folders/%s/invitations' % folder_id
	headers = {'Authorization': 'Bearer %s' % token, 'X-Dropbox-Perform-As-Team-Member': inviter}
	invitee = json.dumps([u'%s' % invitee])
	data = {'uids': invitee, 'suppress_notifications': True, 'invitee_role': invitee_role}

	r = requests.post(url, headers=headers, data=data)

	if r.status_code == 200:
		return r.json()['invitations'][0]['invite_id']
	else:
		print('HTTP error %s (%s - %s)' % (r.status_code, r.reason, r.text))
		return False

def accept_invitation(token, invitee, invitation):
	url = 'https://api.dropboxapi.com/1/invitations/%s/accept' % invitation
	headers = {'Authorization': 'Bearer %s' % token, 'X-Dropbox-Perform-As-Team-Member': invitee}
	data = {}

	r = requests.post(url, headers=headers, data=data)

	if r.status_code == 200:
		return True
	else:
		print('HTTP error %s (%s - %s)' % (r.status_code, r.reason, r.text))
		return False	

def unshare_folder(token, owner, folder):
	url = 'https://api.dropboxapi.com/1/shared_folders/%s/unshare' % folder
	headers = {'Authorization': 'Bearer %s' % token, 'X-Dropbox-Perform-As-Team-Member': owner}
	data = {'keep_files': True}

	r = requests.post(url, headers=headers, data=data)

	if r.status_code == 200:
		return True
	else:
		print('HTTP error %s (%s - %s)' % (r.status_code, r.reason, r.text))
		return False

def get_member_ids(token):
	url = 'https://api.dropbox.com/1/team/members/list'
	headers = {'Authorization': 'Bearer %s' % token, 'Content-Type': 'application/json'}
	data = {}
	members = []

	r = requests.post(url, headers=headers, data=json.dumps(data))

	if r.status_code == 200:
		profiles = r.json()['members']
		for i in profiles:
			members.append([i['profile']['email'], i['profile']['member_id']])
	else:
		print('HTTP error %s (%s - %s)' % (r.status_code, r.reason, r.text))

	return members

def find_member(email, member_list):
	try:
		user = next(subl for subl in member_list if email in subl)
		return user[1]
	except StopIteration:
		return False