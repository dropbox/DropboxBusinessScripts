# DropboxBusinessScripts
## Dropbox Business & Dropbox Enterprise Scripts

Included here are scripting resources to serve as a base for common Dropbox Business and Dropbox Enterprise tasks. 

### Licensing

All scripts within this folder are covered by the Apache License as described in LICENSE.txt.

##### Please carefully note: 

> "Disclaimer of Warranty. [...] the Work (and each Contributor provides its Contributions) on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied, including, without limitation, any warranties or conditions of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A PARTICULAR PURPOSE. You are solely responsible for determining the appropriateness of using or redistributing the Work and assume any risks associated with Your exercise of permissions under this License."

### Script Conventions

Every script should:

- Have comments at top of file regarding usage (including API permission)
- Take command-line arguments.  (script) -h should print usage/description
  - Use argparse for python
  - Use commons-cli for java
  - Javascript/php/powershell equivalents?
— Prompt for API token (and tell you type/permission level it needs)
  - We *don’t* want to save the token in the file, or pass it as an arg on CLI (too easy to accidentally expose in file/bash_history)
- Use camel-cased file names (no dashes). 3-5 words.  Roughly equivalent scripts in the same language should share the same name.

### Tips

- For help in powershell: `Get-Help .\filename.ps1`
- Internationalization:  Test scripts with some non-latin characters in file strings / usernames when possible.  For example, python needs to call reload(sys) / sys.setdefaultencoding('UTF8') to be happy with nonlatin strings.

### Future Plans

Omissions / scripts to add:

- Scripts to get/manage list of shared links?  Scripts to add password/permission to links
- PHP example (anything)
- .NET / C# example (anything)
- Anything audit-log centric in another language (python/php)
- Groups
- Shared folder API & device management API in beta.  Have examples prepared (but don’t publish to GIT until public)
  - Script that takes white/blacklist (of region, apps, devices) and disconnect accordingly
  - Script that takes list of members, adds them to group if not present.