Red Hat Enterprise Virutualization Export Script
================================================

RHEV VM export and import to remote RHEV site.

Requirements
------------
This script was tested on RHEV 3.2 environments.
To run this scripts it require rhevm-sdk packages provide

This script is created in order to export VM in local sit
then import VM on remote RHEV site automatically.

How to work
------------
1. Get informations local and remote RHEV environment.
2. Shutdown VM on local site
3. Export VM on local site
4. Replace VM disk image metadata and ovf data
5. Copy with rsync exported image and data files to remot
6. Import VM on remote site
7. Start VM on remote site


