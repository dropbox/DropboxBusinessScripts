# Enterprise Installer

A set of scripts designed to allow for gated distribution of Dropbox desktop client updates.

# Methodology
The Enterprise Installer works via two scripts:
  - Dropbox Enterprise Installer QA
 Intended to run on QA systems. Acts as the gating mechanism to determine when a release is suitable for deployment to the production environment. 
  - Dropbox Enterprise Installer
 Run as a login script, this will perform the installation of a Dropbox desktop client that has been released from the QA environment. It will also disable auto-updating post-installation to ensure that clients only update via this process.

![High level Architecture](https://www.dropbox.com/scl/fi/mru2cvr3lnnyenh3f5kgf/DbxEI_arch_high_level.JPG?raw=1 "High Level Architecture")

The Enterprise Installer scripts assume two environments will be used
- QA
    - This environment will have one or more devices configured to accept Dropbox updates directly and automatically (standard mode of client operation)
    - The Enterprise Installer QA script will be scheduled to run at least daily on a device within the environment
- Production
    - This environment will use the Enterprise Installer installation script to deploy QA approved Dropbox client installations at the point of login
    - The Enterprise Installer installation script must be configured to run at login on all devices

The process of getting a release out to production works as follows:
1. QA device(s) update from Dropbox directly
2. Enterprise Installer QA script is run, each new version seen goes into a version history which is then checked against either an N-x or minimum age gating mechanism.
3. When a release passes the gating mechanism, it is downloaded, verified, and moved to some form of intermediate storage (typically a UNC path) and a release version file is produced containing the currently approved version.
4. On the next run of the Enterprise Installer installation script (at login) it will check for a new release version, retrieve it from the intermediate storage, and then perform a silent installation on the endpoint device. When this installation is complete the tasks that would normally auto-update the endploint device will be disabled to prevent updates from happening out-of-band from the Enterprise Installer process.
---
# Usage
The Enterprise Installer is open source software and is unsupported by Dropbox.
*__Use at your own risk, YMMV, caveat emptor, here be dragons, and all other pertinent warnings apply.__*