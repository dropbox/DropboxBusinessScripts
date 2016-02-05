# Deprovisions users from a csv file and wipes data off all of their devices
# Currently set to suspend, may be changed to delete

#variables to change
$filepath = Read-Host -Prompt 'Input the path to your .csv file'
$logfile = Read-Host -Prompt 'Input the path to a blank .txt file for logging'
$authtoken = Read-Host -Prompt 'Input your token used to deprovision'
$token = "Bearer " + $authtoken

# uri deletes user
# $uri = "https://api.dropboxapi.com/2/team/members/remove"

# uri suspends user
$uri = "https://api.dropboxapi.com/2/team/members/suspend"

function teamremoveMember($headerBody)
{
	$result = Invoke-RestMethod -Uri $uri -Headers @{ "Authorization" = $token } -Body $headerBody -ContentType application/json -Method Post
	write-host "[-] Done "
}

$memberinfo = Import-Csv $filepath
$count = 0
foreach($line in $memberinfo)
{
	$email = $line.email
	$headerBody = '{"user": {".tag": "email", "email": "' +  $email + '"},"wipe_data": true}'
	 
	Write-Host "[*] Suspending team member: " $email
		$sw = [Diagnostics.Stopwatch]::StartNew()
		teamremoveMember $headerBody
		$sw.Stop()
		Write-Host "[*]" $sw.Elapsed.TotalSeconds "seconds"
		$outstring = $count.ToString() + "," + $sw.Elapsed.TotalSeconds.ToString()
		$outstring | Out-File -FilePath $logfile -Append
		$count++ 
}