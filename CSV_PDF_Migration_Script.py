## Script for scanning a CSV file for links to documents, download those documents, 
## and scan the subsequent files (assuming PDF) for additional content to download

## THIS VERSION ASSUMES FILES WILL BE PLACED IN THE DROPBOX FOLDER USING THE DESKTOP APP. MODIFICATIONS ARE NEEDED FOR USE WITH DROPBOX API

import csv
import requests
import re
import PyPDF2
from os.path import basename
import os
from urllib.parse import urlparse
import pikepdf
from urllib.request import Request, urlopen

## Open CSV file (enter path of CSV file below)
f = open('file.csv')
csv_f = csv.reader(f)
for row in csv_f:
	
	url = row[3]
	projectid = row[0]

	## Create project folder in Dropbox if not exist
	if not os.path.exists('PATH_TO_DROPBOX_FOLDER'+projectid):
		os.makedirs('PATH_TO_DROPBOX_FOLDER'+projectid)
	
	## Download file and add to project folder
	myfile = requests.get(url, allow_redirects=True)
	hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
       'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
       'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
       'Accept-Encoding': 'none',
       'Accept-Language': 'en-US,en;q=0.8',
       'Connection': 'keep-alive'}
	req = Request(url, headers=hdr)
	response = urlopen(req)
	fname = basename(response.url)
	
	print('Downloading '+str(fname)+" for project "+projectid)
	
	## Here is where the file is saved to Dropbox. Dropbox API can be used here to upload directly
	open('PATH_TO_DROPBOX_FOLDER'+projectid+'/'+str(fname), 'wb').write(myfile.content)

	## Download files in PDF
	file = "PATH_TO_DROPBOX_FOLDER"+projectid+"/"+str(fname)
	pdf_file = pikepdf.Pdf.open(file)
	urls = []
	# iterate over PDF pages
	for page in pdf_file.pages:
	    for annots in page.get("/Annots") or []:
	        if annots is not None:
		        uri = annots.get("/A").get("/URI")
		        ## Find URLs in PDFs and download linked files
		        if uri is not None:
		            print("[+] URL Found:", uri)
		            uriString = str(uri)
		            innerfile = requests.get(uriString, allow_redirects=True)
		            reqInner = Request(uriString, headers=hdr)
		            responseInner = urlopen(reqInner)
		            fnameInner = basename(responseInner.url)
		            open('PATH_TO_DROPBOX_FOLDER'+projectid+'/'+str(fnameInner), 'wb').write(innerfile.content)

### Done!