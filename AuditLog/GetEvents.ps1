param (
	[string]$start, # mm/dd/yyyy hh:mm:ss
	[string]$end, # mm/dd/yyyy hh:mm:ss
	[string]$category # apps, devices, groups, logins, members, passwords, sharing, team_admin_actions 
	)

$epochDate = "1/1/1970 00:00:00"
$object = New-Object psobject

if($start) {
	$start = (New-TimeSpan -Start $epochDate -End (Get-Date -Date $start)).TotalSeconds
	$object | Add-Member -MemberType NoteProperty -Name start_ts -Value ([int]$start * 1000)
}

if($end) {
	$end = (New-TimeSpan -Start $epochDate -End (Get-Date -Date $end)).TotalSeconds
	$object | Add-Member -MemberType NoteProperty -Name end_ts -Value ([int]$end * 1000)
}

if($category) {
	$object | Add-Member -MemberType NoteProperty -Name category -Value $category
}

#Write-Host (ConvertTo-Json $object)

# Prompt for Team Auditing permission
$token = Read-Host -Prompt "Enter your Dropbox Business API App token (Team Auditing permission): "
$token = "Bearer $token"

Write-Host
Write-Host "Audit Log:" -ForegroundColor Green
Write-Host

$has_more = $true
$cursor = $null

# Continue to call get_events as long as there are more events
while($has_more) {

	if($cursor) {
		if($object.cursor) {
			$object.cursor = $cursor
		} else {
			$object | Add-Member -MemberType NoteProperty -Name cursor -Value $cursor
		}
	}

	# Make API Call for events
	$report = Invoke-RestMethod -Uri https://api.dropbox.com/1/team/log/get_events -Body (ConvertTo-Json $object) -ContentType application/json -Headers @{Authorization = $token } -Method Post
	$report.events

	$has_more = [System.convert]::ToBoolean($report.has_more)
	$cursor = $report.cursor

}



