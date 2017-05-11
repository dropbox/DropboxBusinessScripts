#Dropbox Powershell Enterprise Installer - QA Tool
#Version 1.0
<# 
This script can be used to download and test a version of Dropbox for later distribution via internal software 
delivery mechanisms. 

Alternatively this is the counterpart script to Dropbox Enterprise Start Installer.ps1 and will help you push
a specified build to your clients using PowerShell locally on those machines.

This should be automated using a scheduled task to run on a daily basis.

This script MUST be signed to run and MUST be run as an admin or SYSTEM 

#>

# Configuration Variables
$MinPrevVersions = 0 # Min number of versions back from current (N-x) before a release can be moved to production
$MinAgeDays = 0 # Min age in days before a release will be move to production
$Verbose = 0 # Default to silent (0), use 1 for verbose output
$VersionFile = "$env:Temp\dropbox.ver" # Location to place production approved version file
$Source =  $env:TEMP # Location to place installer files
$Testing = 0 # Default to production (0), for testing change to 1

######################## NO EDITING BELOW THIS LINE ########################

# Globals
$clientVerKey = "HKLM\SOFTWARE\WOW6432Node\Dropbox\Client"
$AppKey = "HKLM\SOFTWARE\WOW6432Node\DropboxQA\"
$VerKey = "HKLM\SOFTWARE\WOW6432Node\DropboxQA\Versions"

$now = Get-Date

###### MAIN ######
Function Main {
    Initialize

    If( $MinPrevVersions -eq 0 -and $MinAgeDays -eq 0 ) {
        Log -Message "No Previous version or Age set. Aborting" -Code 31 -Type 'Error'
    }
    Log -Message "Minimum Prevous Versions: $MinPrevVersions" -Code 32 -Type 'Information'
    Log -Message "Minimum age of release: $MinAgeDays days" -Code 33 -Type 'Information'
    Log -Message "Version file path: $VersionFile" -Code 34 -Type 'Information'

    try {
        # Check for the current version of Dropbox that is installed
        $CurrentDbxVer = Get-ItemPropertyValue -Path "Registry::$ClientVerKey" -ErrorAction Stop -Name Version
        Log -Message "Current Dropbox version is: $CurrentDbxVer" -Code 2 -Type 'Information'
        
        # Write new version information if it doesn't exist
        If ( -Not ( Test-RegistryValue $VerKey $CurrentDbxVer) ) {
            Log "Adding version history entry for client version $CurrentDbxVer" -Code 3 -Type 'Information'
            Set-ItemProperty -path "Registry::$VerKey" -Name $CurrentDbxVer -Type "MultiString" -Value $CurrentDbxVer, $now
        } else {
            Log "Version already exists in version history" -Code 4 -Type 'Information'
        }
    } catch {
        Log -Message "Could not find current Dropbox Client version: $_" -Code 5 -Type 'Error'
    }

    
    try {
        # Collect version history entries, make sure they are sorted chronologically
        $VersionHistory = New-Object System.Collections.Generic.List[System.Object]
        $Versions = Get-ItemProperty -Path "Registry::$VerKey" -ErrorAction Stop
        $Versions.PSObject.Properties | ForEach-Object {
            If ( !($_.Name -Like 'PS*') ) {
                #Write-Host $_.Name ' = ' $_.Value
                $VersionHistory.Add($_.Value)
            }
        }

        # Sort the version history from highest to lowest (newest to oldest)
        if ( $VersionHistory.Count -gt 1 ) { #Only sort of there's something to actually sort
            $VersionHistory = $VersionHistory | sort-object @{Expression={$_[0]}; Ascending=$false}
        }
        Log -Message "Newest Client Version is: $($VersionHistory[0][0])"  -Code 6 -Type 'Information'
        
        # Check for N-1 version count
        if ( $MinPrevVersions -gt 0 ) {
            Log -Message "Determining N-$MinPrevVersions version number..." -Code 7 -Type 'Information'
            if ( -Not ($VersionHistory.Count -lt $MinPrevVersions + 1) ) {
                $PreviousReleaseVersion = $VersionHistory[$MinPrevVersions]
                Log -Message "N-$MinPrevVersions client version is: $($PreviousReleaseVersion[0])" -Code 8 -Type 'Information'
            } else {
                Log -Message "Not enough version history to select a release for deployment." -Code 9 -Type 'Information'
                Log -Message "Versions required for N-$MinPrevVersions release selection: $($MinPrevVersions + 1), Current version history size: $($VersionHistory.Count)" -Code 10 -Type 'Information'
            }
        } else {
            Log -Message "No previous version count provided, skipping checks..." -Code 11 -Type 'Information'
        }

        # Check for X days old
        if ( $MinAgeDays -gt 0 ) {
            foreach ( $Version in $VersionHistory ) {
                $VersionDate = (Get-Date $Version[1]).AddDays($MinAgeDays)
                if ( $VersionDate -lt $now ) {
                    $MinimumAgeVersion = $Version
                    Log -Message "$MinAgeDays day minimum age version is $($MinimumAgeVersion[0])" -Code 12 -Type 'Information'
                    break
                }
            }

            if ( -Not $MinimumAgeVersion ) {
                log -Message "No version old enough to be selected for deployment." -Code 13 -Type 'Information'
                Log -Message "No version in the current version history is older than $MinAgeDays days" -Code 14 -Type 'Information'
            }

         } else {
            Log -Message "No minimum age requirement provided, skipping checks..." -Code 15 -Type 'Information'
        }

        <#  Compare N-x version vs min age version and pick a "winner"
            Generally we just want to err on the conservative side here
            so we'll compare and just pick the "oldest" version - more accurately
            we'll take the "lowest" version number if both release selection methods
            return a valid version number
        #>
        if ( $PreviousReleaseVersion -and $MinimumAgeVersion ) {
            Log -Message "There are valid versions for both gating mechanisms!" -Code 16 -Type 'Information'
            if ( $PreviousReleaseVersion[0] -lt $MinimumAgeVersion[0] ) {
                Log -Message "Using N-$MinPrevVersions release: $($PreviousReleaseVersion[0])" -Code 17 -Type 'Information'
                $ReleaseVersion = $PreviousReleaseVersion
            } else {
                Log -Message "Using $MinAgeDays day minimum age release: $($MinimumAgeVersion[0])" -Code 18 -Type 'Information'
                $ReleaseVersion = $MinimumAgeVersion
            }
        } elseif ( $PreviousReleaseVersion ) {
            Log -Message "Using N-$MinPrevVersions release: $($PreviousReleaseVersion[0])" -Code 19 -Type 'Information'
            $ReleaseVersion = $PreviousReleaseVersion
        } elseif ( $MinimumAgeVersion ) {
            Log -Message "Using $MinAgeDays day minimum age release: $($MinimumAgeVersion[0])" -Code 20 -Type 'Information'
            $ReleaseVersion = $MinimumAgeVersion
        } else {
            Log -Message "No suitable release versions found..." -Code 21 -Type 'Information'
        }
    } catch {
        Log -Message "Could not determine valid release version: $_" -Code 22 -Type 'Error'
    }
    if($ReleaseVersion -is [system.array] -and $ReleaseVersion[0] -eq '0'){ #When running for the first time or before a newer version has been released
        Log -Message "Running latest build and no historical versions exist yet, aborting." -Code 30 -Type 'Error'
    }
        # Write out release information
        if ( $ReleaseVersion ) {
            #Test that version still available to download
            $url = "https://clientupdates.dropboxstatic.com/client/Dropbox%20" + $ReleaseVersion[0] + "%20Offline%20Installer.exe"
            $fileName = Split-Path $url -Leaf 
            $webClient = New-Object System.Net.WebClient
            $destinationPath = $Source + "\DropboxOfflineInstaller.exe" #Overwrite any pre-existing installer
            Log -Message 'Checking Dropbox installer download is available' -Code 23 -Type 'Information'
            try{
               if($Testing -ne 1){
                    $webClient.DownloadFile($url,$destinationPath) #Download the file to check if its still active
                    $file = Get-AuthenticodeSignature $destinationPath #Examine the Authenticode signature
                    if($file.Status -eq "Valid") {
                        Log -Message 'Dropbox version valid and Authenticode approved' -Code 24 -Type 'Information'
                    }else{
                        Log -Message 'Dropbox version failed Authenticode check, aborting.' -Code 25 -Type 'Error'
                    }
               } #Don't download if in testing mode
            }catch{
                Log -Message 'Cannot download Dropbox version, aborting.' -Code 26 -Type 'Error'
            }
            Log -Message "Writing version $($ReleaseVersion[0]) to $VersionFile..." -Code 27 -Type 'Information'
            try {
                $ReleaseVersion[0] | Out-File $VersionFile
            } catch {
                Log $_
            }
        }
    Shutdown
}


#######################
###### Functions ######
#######################
Function Initialize {

    # Perform startup checks
    #Check to see if the user has the Administrator role on the machine, if not die
    If (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(`
        [Security.Principal.WindowsBuiltInRole] "Administrator")){
        Log -Message "You do not have Administrator rights to run this script! Please re-run this script as an Administrator!" -Code 1 -Type 'Error'
    }
    #Check if script is signed, and valid
    if ( -Not $Testing ) {
        $self = Get-AuthenticodeSignature -FilePath $MyInvocation.ScriptName
        If ( $self.status -ne 'Valid' ) {
            Log -Message 'Script not signed, aborting.' -Code 35 -Type 'Error'
        }
    }

    #Create or update a new Event Log
    If ( ![System.Diagnostics.EventLog]::SourceExists("Dropbox PowerShell - QA") ) {
        try {
            Write-Host "Creating new Event Log Source: Dropbox PowerShell - QA"
            New-EventLog –LogName "Application" –Source "Dropbox PowerShell - QA" 
        } catch {
            Write-Host 'Unable to create Dropbox PowerShell - QA event log, please contact the Helpdesk.'
            Exit 1
        }
    }

    # Prepare registry
    If ( -Not ( Test-Path "Registry::$VerKey") ) {
        try {
            New-Item -Path "Registry::$VerKey" -ItemType RegistryKey -Force
            Log -Message "Created Registry key: $VerKey" -Code 28 -Type 'Information'
        } catch {
            Log -Message "Cannot create registry key $VerKey" -Code 29 -Type 'Error'
        }
    }
}

Function Shutdown {
    # Perform any finalizing tasks here
}

Function Test-RegistryValue($Key, $Name)
{
    (Get-ChildItem (Split-Path -Parent -Path "Registry::$Key") | Where-Object {$_.PSChildName -eq (Split-Path -Leaf $Key)}).Property -contains $Name
}

Function Log {
    Param( $Message, $Code = 0, $Type = 'Information')
    
    if ( $Type -eq "Error" ) {
        Write-Warning $Message # not ideal, but less verbose than write-error
    } elseif($Verbose -eq 1) {
        Write-Host $Message
    } elseif($Verbose -eq 0) {
        Write-Information $Message
    }
    Write-EventLog -LogName "Application" -Source "Dropbox PowerShell - QA" -EventID $Code -EntryType $Type -Message $Message
    if ( $Type -eq "Error" ) {
        Shutdown # do any cleanup
        Exit 1  #Die if fatal 'We'll settle this the old navy way; The first guy to die. LOSES!'
    }
}

Main # Invoke Main Function
<#MIT License
Copyright (c) 2017 Chuck Hirstius & John Bradshaw
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