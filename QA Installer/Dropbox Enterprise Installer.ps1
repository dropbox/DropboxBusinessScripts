#Dropbox Powershell Enterprise Installer
#Version 0.4
<# 
Download and install the latest version of Dropbox for the purposes of Enterprise deployment
This script can be run as part of a user logon script

Update the $approved_ver with the value of your choice, this can be centralised
using either:
* Preset value in this Script
* Network Share (I appreciate the irony)
* Dropbox shared link, this must be publically accessible

Decide which one is appropriate for your environment and use as appropriate

This script MUST be signed to run and MUST be run as an admin or SYSTEM

#>

$source =  $env:TEMP #Change this to a download directory of your choosing
$arguments = '/s' #Change /s to /NOLAUNCH to prevent client start
$testing = 1 #Change to 0 to install/update

#Choose how you will find the correct version number for Dropbox to install
$approved_ver = '' #'26.1.9' 
$approved_path = '' #'' #'\\NETWORKFILESYSTEM\Directory\approved.txt'
$approved_link = "" #Use a Dropbox shared link (must be publically accessible)

###### NO EDITTING BELOW THIS LINE #######
#Handle errors by displaying a message and logging
Function ErrorHandler{
    Param($Message, $Code, $Type)
    Write-host $Message
    Write-EventLog -LogName "Application" -Source "Dropbox PowerShell" -EventID $Code -EntryType $Type -Message $Message
    if($Type -eq "Error"){exit} #Die if fatal
}

#Check to see if at least one version
if(!$approved_ver -and !$approved_path -and !$approved_link){
    ErrorHandler -Message 'Dropbox installation version not specfied. Please contact the Helpdesk.' -Code 100 -Type 'Error'
}

#Create or update a new Event Log
If ([System.Diagnostics.EventLog]::SourceExists("Dropbox PowerShell")){
}else{
    try{
        New-EventLog –LogName "Application" –Source "Dropbox PowerShell" 
    }catch{
        ErrorHandler -Message 'Unable to create Dropbox event log, please contact the Helpdesk.' -Code 99 -Type 'Error'
    }
}

#Check to see if the user has the Administrator role on the machine, if not die
If (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(`
    [Security.Principal.WindowsBuiltInRole] "Administrator")){
    ErrorHandler -Message "You do not have Administrator rights to run this script! Please re-run this script as an Administrator!" -Code 1 -Type 'Error'
}

#Grab the file if using Dropbox
If ($approved_link) {
    #Check to see if link is live
    $approved_link = $approved_link -replace "dl=0", "dl=1"
    $wc = new-object system.net.WebClient
    $webpage = $wc.DownloadData($approved_link)
    $approved_ver = [System.Text.Encoding]::ASCII.GetString($webpage)
    #Check that the first line of the response has a version number   
    if([regex]::match($approved_ver,'^\d{1,3}\.\d{1,3}\.\d{1,3}').success -eq 0){
        ErrorHandler -Message 'Unable to confirm version number. Please contact the Helpdesk.' -Code 2 -Type 'Error'
    }
}

#Grab the file if using UNC Path
If ($approved_path) {
    try{
        $approved_ver = Get-Content -Path $approved_path
    }catch{
        ErrorHandler -Message 'Cannot connect to file share. Dropbox cannot install please contact the Helpdesk.' -Code 3 -Type 'Error'
    }
}

#Validate version number
If (-NOT ($approved_ver -match '^\d{1,3}\.\d{1,3}\.\d{1,3}')){
    ErrorHandler -Message 'Version number corrupted! Please contact the Helpdesk.' -Code 4 -Type 'Error'
} 

#Validate your inputs!
$approved_ver = [regex]::Match($approved_ver,'^\d{1,3}\.\d{1,3}\.\d{1,3}')

#Check to see if Dropbox is installed
try{
    #Find the Dropbox client version number from the registry
    #$client_ver1 = Get-ItemProperty -Path 'Registry::HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\DropboxUpdate\Update\Clients\{CC46080E-4C33-4981-859A-BBA2F780F31E}\' -ErrorAction Stop | Select-Object -ExpandProperty pv
    $client_ver2 = Get-ItemProperty -Path 'Registry::HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Dropbox\Client\' -ErrorAction Stop | Select-Object -ExpandProperty Version
}catch{
    $client_ver2 = 0
    ErrorHandler -Message 'Dropbox not installed...' -Code 5 -Type 'Information'
}

#Check version of Dropbox and install update if required
If ($client_ver2 -eq 0 -or ($client_ver2 -lt $approved_ver)){

    $url = "https://clientupdates.dropboxstatic.com/client/Dropbox%20" + $approved_ver + "%20Offline%20Installer.exe"
    $fileName = Split-Path $url -Leaf 
    $webClient = New-Object System.Net.WebClient
    $destinationPath = $source + "\DropboxOfflineInstaller.exe" #Overwrite any pre-existing installer
    ErrorHandler -Message 'Downloading Dropbox' -Code 6 -Type 'Information'
    try{
        if($testing -ne 1){
            $webClient.DownloadFile($url,$destinationPath)
            $file = Get-AuthenticodeSignature $destinationPath
            if($file.Status -eq "Valid") {
                ErrorHandler -Message 'Dropbox version valid and Authenticode approved' -Code 11 -Type 'Information'
            }else{
                ErrorHandler -Message 'Dropbox version failed Authenticode check. Installation failed. Please contact the Helpdesk' -Code 12 -Type 'Error'
            }
        } #Don't download if in testing mode
    }catch{
        ErrorHandler -Message 'Cannot download Dropbox. Please contact the Helpdesk.' -Code 7 -Type 'Error'
    }
    try{
        if($testing -ne 1){Invoke-Expression -Command "$destinationPath $arguments"} #Don't install if in testing mode
        ErrorHandler -Message 'Installing Dropbox...' -Code 8 -Type 'Information'
    }catch{
        ErrorHandler 'Cannot install Dropbox. Please contact the Helpdesk.' -Code 9 -Type 'Error'
    }
}

#Disable scheduled tasks, this should also be enforced by GPO, this is needed to prevent client updating
#Stop any running Dropbox tasks
try{
    Stop-ScheduledTask -TaskName "DropboxUpdateTaskMachineCore" -ErrorAction SilentlyContinue | Out-Null
    Disable-ScheduledTask -TaskName "DropboxUpdateTaskMachineCore" -ErrorAction SilentlyContinue | Out-Null
    Stop-ScheduledTask -TaskName "DropboxUpdateTaskMachineUA" -ErrorAction SilentlyContinue | Out-Null
    Disable-ScheduledTask -TaskName "DropboxUpdateTaskMachineUA" -ErrorAction SilentlyContinue | Out-Null
}catch{
    ErrorHandler -Message 'Could not disable some or all of the Dropbox Update tasks, please contact the Helpdesk.' -Code 10 -Type 'Error'
}

<#MIT License
Copyright (c) 2017 John Bradshaw
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.#>