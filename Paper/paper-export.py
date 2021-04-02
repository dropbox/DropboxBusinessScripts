# File: paper-export.py
# Export Paper Docs Tool
# Version 1.0
# Author: Marcel Ribas - @macribas
# Date: 3/31/2021

# Python script to export Paper Docs from a Dropbox account. It can export in either HTML or Markdown.
# It only works in accounts that have Paper In the FileSystem (PiFS). Script checks the account for that condition.
# Does not work recursively, on purpose. You need to select the folders where your Paper docs are. Saves files in the working local folder. 
# Once you are comfortable with running this, then you can modify it to work recursively. 
# Your API key needs to have Full Dropbox access and files.content.read scope.

import dropbox
import os

# Dropbox
try:
	dbx = dropbox.Dropbox('<YOUR_API_KEY_HERE>')
	# check if account has PiFS
	features = dbx.users_features_get_values([dropbox.users.UserFeature.paper_as_files])
	pifs = features.values[0].get_paper_as_files().get_enabled()
except dropbox.exceptions.AuthError:
	print("It was not possible to connect to your Dropbox account. Please try another token.")
	print("You need the files.content.read scope")
	quit()

if not pifs:
	print("This account does not have Paper In The FileSystem (PiFS) enabled")
	quit()

while True:
	path = input("Enter the Dropbox path for your Paper docs (<RETURN> for the root folder): ")
	if path.startswith('/') or not path:
		break;
	else:
		print("Invalid folder name, please try again.")

while True:
	go_on = input("This process might take a while, depending on the size of the folder you are traversing. Continue (Y or N)? ")
	if go_on.upper() == 'Y':
		break;
	elif go_on.upper() == 'N':
		quit()

print("Processing")

# Check if folder exists
try: 
	folder = dbx.files_list_folder(path)
	cursor = folder.cursor
except dropbox.exceptions.DropboxException:
	print("Could not find folder {0}".format(path))
	quit()
    
# if file is paper doc, put it in list
paper_docs = [file.path_display for file in folder.entries if isinstance(file, dropbox.files.FileMetadata) if not file.is_downloadable if os.path.splitext(file.path_lower)[1] == ".paper"]

while folder.has_more:
	print("Still working")
	folder = dbx.files_list_folder_continue(cursor)
	cursor = folder.cursor
	paper_docs += [file.path_display for file in folder.entries if isinstance(file, dropbox.files.FileMetadata) if not file.is_downloadable if os.path.splitext(file.path_lower)[1] == ".paper"]

size = len(paper_docs)
if size == 0:
	print("You don't have any Paper docs in this path. ")
	quit()
else:
	if path:
		folder_name = path
	else:
		folder_name = "the root folder"
	print("You have {0} Paper docs in {1}.".format(size,folder_name))

while True:
	export = input("Do you want to export these to your computer? (Y/N) ")
	if export.upper() == 'Y':
		break;
	elif export.upper() == 'N':
		quit()

print("These Paper docs will be exported to the folder where you are running this script from.")

while True: 
	format = input("Which format do you want to export as? (1) HTML or (2) Markdown? (3) to quit: ")
	if format == '1':
		export_as = ("html",".html")
		break
	elif format == '2':
		export_as = ("markdown",".md")
		break
	elif format == '3':
		quit()
	else:
		print("Invalid format")

for paper_doc in paper_docs:
	folder, filename = os.path.split(paper_doc)
	basename, ext = os.path.splitext(filename)

	print("Exporting {0} as {1}".format(paper_doc, basename + export_as[1]))

	with open(basename + export_as[1], "wb") as f:
		metadata, res = dbx.files_export(path=paper_doc,export_format=export_as[0])
		f.write(res.content)

print("Export completed!")
