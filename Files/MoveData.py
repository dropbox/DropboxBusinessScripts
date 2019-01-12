from __future__ import print_function

import requests


def move_data(token, member_id, from_path, to_path):
	url = 'https://api.dropboxapi.com/1/fileops/move'
	headers = {'Authorization': 'Bearer %s' % token, 'X-Dropbox-Perform-As-Team-Member': member_id}
	data = {'root': 'auto', 'from_path': from_path, 'to_path': to_path}

	print('Moving "%s" to "%s" (member_id: %s)' % (from_path, to_path, member_id))

	r = requests.post(url, headers=headers, data=data)

	if r.status_code == 200:
		print('Success!')
		return True
	else:
		print('HTTP error %s - %s (%s)' % (r.status_code, r.reason, r.text))
		return False