import pprint                         # Allows Pretty Print of JSON

#############################################
# Define a Class to represent a group
#############################################
class Group:
	def __init__(self):
		self.group_name = ''
		self.group_members = ''
		self.group_permission = ''
		self.group_type = ''

	def __init__(self, name, members_count, permision, group_type):
		self.group_name = name
		self.group_members = members_count
		self.group_permission = permision
		self.group_type = group_type


#############################################
# Define a Class to represent a user
#############################################
class User:
	def __init__(self):
		self.user_access_type = ''
		self.user_permission_inherited = ''
		self.user_email = ''
		self.user_on_team = ''
		self.user_name = ''

	def __init__(self, user_access_type, user_permission_inherited, user_email, user_on_team, user_name):
		self.user_access_type = user_access_type
		self.user_permission_inherited = user_permission_inherited
		self.user_email = user_email
		self.user_on_team = user_on_team
		self.user_name = user_name


#############################################
# Define a Class to represent a shared folder
#############################################
class SharedFolder:
	def __init__(self):
		self.team_member_id = ''
		self.team_member_name = ''
		self.team_member_email = ''
		self.email_is_verified = ''
		self.account_status = ''
		self.is_team_folder = ''
		self.is_part_of_team_folder = ''
		self.folder_name = ''
		self.share_folder_id = ''
		self.time_invited = ''
		self.path_lower = ''
		self.mount_status = ''      # If path_lower is empty folder is UNMOUNTED
		self.preview_url = ''
		self.folder_permission = ''
		self.groups = []			# List of Groups with access
		self.invitees = []			# List of Invited users
		self.users = []				# List of Users with access


	def getPathLower(self):
		if( self.path_lower == None ):
			return ''
		else:
			return self.path_lower 

	def addGroup(self, name, members_count, permision, group_type):
		grp = Group( name, members_count, permision, group_type )
		self.groups.append( grp )

	def addUser(self, user_access_type, user_permission_inherited, user_email, user_on_team, user_name):
		usr = User( user_access_type, user_permission_inherited, user_email, user_on_team, user_name)
		self.users.append( usr )

	def getUsers(self):
		#pprint.pprint ( len( self.users ))
		return self.users

	def getExternallyOwnedFolderRow(self):
		row = []

		extUser = None

		# Find the user that is external owner
		for aUser in self.users:
			#print ( 'aUser: %s | %s | %s | %s' % (aUser.user_name, aUser.user_email, aUser.user_access_type, aUser.user_on_team)) 
			if ( aUser.user_access_type == 'owner' and aUser.user_on_team == False ):
				extUser = aUser
				break

		row.append( '' if (extUser == None or extUser.user_email == None) else extUser.user_email ) #self.team_member_email  #'Owner email'
		row.append( '' if (extUser == None or extUser.user_name == None) else extUser.user_name ) #self.team_member_name  #'Owner Name',
		row.append( self.folder_name ) #'Folder Name'
		row.append( self.getPathLower() ) #'Folder Path'
		row.append( self.share_folder_id ) #'Share Folder ID'
		row.append( self.mount_status ) #'Folder Mount Status'
		row.append( self.team_member_email ) #'User Email'
		row.append( self.folder_permission ) #'User Access Type'
		row.append( str(False) ) #'User on Team'
		row.append( '' ) #'Group Name'
		row.append( '' ) #'Group Members'
		row.append( '' ) #'Group Permission'
		row.append( '' ) #'Group Type'
		row.append( str(False) ) # 'Team owned folder'

		return row


	def getOwnerOwnedFolderRows(self):

		rows = []

		# Build a list sharing
		# One row per groups
		for grp in self.groups:
			row = []


			row.append( self.team_member_email ) #'Owner email'
			row.append( self.team_member_name ) #'Owner Name',
			row.append( self.folder_name ) #'Name'
			row.append( self.getPathLower() ) #'Folder Path'
			row.append( self.share_folder_id ) # 'Share Folder ID'
			row.append( self.mount_status ) #'Folder Mount Status'
			row.append( '' ) # Collaborator Email
			row.append( '' ) # Collaborator Permissions
			row.append( '' ) # Collaborator on Team
			row.append( grp.group_name ) #'Group Name'
			row.append( str(grp.group_members) ) #'Group Members'
			row.append( grp.group_permission ) #'Group Permission'
			row.append( grp.group_type ) #'Group Type'
			row.append( str(True) ) # 'Team owned folder'

			rows.append ( row )
		
		# One row per user
		for aUser in self.users:
			row = []

			row.append( self.team_member_email ) #'Owner email',
			row.append( self.team_member_name ) #'Owner Name',
			row.append( self.folder_name ) #'Name'
			row.append( self.getPathLower() ) #'Folder Path'
			row.append( self.share_folder_id ) #'Share Folder ID'
			row.append( self.mount_status ) #'Folder Mount Status'
			row.append( aUser.user_email ) #'User Email'
			row.append( aUser.user_access_type ) #'User Access Type'
			row.append( str(aUser.user_on_team) ) #'User on Team'
			row.append( '' ) #'Group Name'
			row.append( '' ) #'Group Members'
			row.append( '' ) #'Group Permission'
			row.append( '' ) #'Group Type'
			row.append( str(True) ) # 'Team owned folder'

			rows.append ( row )

		return rows

	# Method to check if this folder is owned by the user
	def isOwnedByUser(self):
		return self.folder_permission == 'owner'

	# Method to check if this folder is shared from within a Team Folder
	def isNestedInTeamFolder(self):
		return self.is_part_of_team_folder

	# Method to check if this folder is owned by a team member
	def isOwnedByTeamMember(self):

		# Check that User is owner of folder
		if ( self.isOwnedByUser() ):
			return False

		for aUser in self.users:
			if ( aUser.user_access_type == 'owner' and aUser.user_on_team == True ):
				return True

		return False
