#!/usr/bin/python

from __future__ import print_function
import requests
import requests.exceptions
import json
import ast
import sys
import os

try:
    raw_input
except NameError:
    raw_input = input

"""
A script to intake and set all team-members to a specified member space-limitation in GB. 
It iterates through every team-member, checks if they have a quota set and whether or not it is of
the specified limit. If not, it will change the member's quota to the specified space-limtation. 

Notes:
	- Must have Member Space Limits enabled
	- Members' quotas can't be set to under 25 GB. 
	- Script written and tested using Python 2.7.10
	- Will need a Team Member File Access API token (https://www.dropbox.com/developers/apps)

Uses the following API calls:
	- https://api.dropboxapi.com/2/team/members/list
	- https://api.dropboxapi.com/2/team/members/list/continue
	- https://api.dropboxapi.com/2/team/member_space_limits/get_custom_quota
	- https://api.dropboxapi.com/2/team/member_space_limits/set_custom_quota
"""

try:
    reload(sys)
    sys.setdefaultencoding('UTF8')
except NameError:
    pass  # Python 3 already defaults to utf-8

dfbToken = raw_input('Enter your Dropbox Business API App token (Team Member File Access permission): ')
setLimit = raw_input('Set your preferred Space Limitation (Minimum is 25GB): ')

if int(setLimit) < 25:
	print('Cannot set limit to less than 25GB')
	sys.exit()


# ----------- get members ------------ #
def getDfbMembers():
	print('Working.......................')
	data = {'limit': 1000, 'include_removed': False}
	HEADERS = {}
	HEADERS['Authorization'] = 'Bearer ' +dfbToken
	try:
		r = requests.post('https://api.dropboxapi.com/2/team/members/list',json = data, headers = HEADERS)
		r.raise_for_status()
		resp = json.loads(r.text)
		members = resp['members']
		cursor = resp['cursor']
		more = resp['has_more']
		data = {'cursor': cursor}
		batchCheckQuota(formatMembers(members))
		while more:
			print('Has more, still working.......................')
			r_continue = requests.post('https://api.dropboxapi.com/2/team/members/list/continue',json = data, headers = HEADERS)
			r_continue.raise_for_status()
			resp_continue = json.loads(r_continue.text)
			members = resp_continue['members']
			cursor = resp_continue['cursor']
			more = resp_continue['has_more']
			data = {'cursor': cursor}
			batchCheckQuota(formatMembers(members))
	except requests.exceptions.HTTPError as e:
		sys.stderr.write('ERROR: {}'.format(e))
		sys.stderr.write('\n')


# ----------- format members for batch check ------------ #
def formatMembers(members):
	dataDict = {}
	dataList = []
	for member in members:
		tempDict = {}
		tempDict['.tag'] = 'email'
		tempDict['email'] = member['profile']['email']
		dataList.append(tempDict)
	dataDict['users'] = dataList
	return dataDict


# ----------- batch check quota ------------ #
def batchCheckQuota(membersDict):
	data = membersDict
	HEADERS = {}
	HEADERS['Authorization'] = 'Bearer ' +dfbToken
	r = requests.post('https://api.dropboxapi.com/2/team/member_space_limits/get_custom_quota',json = data, headers = HEADERS)
	quotas = json.loads(r.text)
	dataDict = {}
	setQuotaList = []
	for quota in quotas:
		if 'quota_gb' in quota:
			if (quota['quota_gb'] != int(setLimit)):
				tempDict = {'user':{'.tag':'email','email':str(quota['user']['email'])},'quota_gb':int(setLimit)}
				setQuotaList.append(tempDict)
		else:
			tempDict = {'user':{'.tag':'email','email':str(quota['user']['email'])},'quota_gb':int(setLimit)}
			setQuotaList.append(tempDict)
	dataDict['users_and_quotas'] = setQuotaList
	setQuotas(dataDict)


# ----------- batch set quota ------------ #
def setQuotas(membersDict):
	data = membersDict
	HEADERS = {}
	HEADERS['Authorization'] = 'Bearer ' +dfbToken
	r = requests.post('https://api.dropboxapi.com/2/team/member_space_limits/set_custom_quota',json = data, headers = HEADERS)
	resp = json.loads(r.text)
	for item in resp:
		print('changed: ' + item['user']['email'] + ' to ' + str(item['quota_gb']) + 'GB')

getDfbMembers()
