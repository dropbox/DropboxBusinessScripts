# Prompt for Team Member Management permission
$token = Read-Host -Prompt "Enter your Dropbox Business API App token (Team Member Management permission): "
$token = "Bearer $token"

$object = New-Object psobject
$has_more = $true
$cursor = $null

Write-Host
Write-Host "Team Members:" -ForegroundColor Red
Write-Host

# Continue to call get_events as long as there are more events
while($has_more) {

    if($cursor) {
        if($object.cursor) {
            $object.cursor = $cursor
        } else {
            $object | Add-Member -MemberType NoteProperty -Name cursor -Value $cursor
        }
    }

    # Make API call
    $teammembers = Invoke-RestMethod -Uri https://api.dropbox.com/1/team/members/list -Body (ConvertTo-Json $object) -ContentType application/json -Headers @{
                    Authorization = $token } -Method Post
    $memberCount = 0

    # For every member in the team, display their user details
    foreach ($member in $teammembers.members)
    {
        $given_name = $teammembers.members.Item($memberCount).profile.given_name
        $surname = $teammembers.members.Item($memberCount).profile.surname
        $status = $teammembers.members.Item($memberCount).profile.status
        $member_id = $teammembers.members.Item($memberCount).profile.member_id
        $email = $teammembers.members.Item($memberCount).profile.email
        $external_id = $teammembers.members.Item($memberCount).profile.external_id
        $groups = $teammembers.members.Item($memberCount).profile.groups
        $admin = $teammembers.members.Item($memberCount).permissions.is_admin

        #display
        Write-Host "Name:" $given_name $surname -ForegroundColor Green
        Write-Host "Status:" $status
        Write-Host "Member_Id:" $member_id
        Write-Host "Email:" $email
        Write-Host "External_Id:" $external_id
        Write-Host "Groups:" $groups
        Write-Host "Admin:" $admin
        Write-Host 

        $memberCount++
    }

    $has_more = [System.convert]::ToBoolean($teammembers.has_more)
    $cursor = $teammembers.cursor

}