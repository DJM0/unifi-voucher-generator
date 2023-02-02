#!/bin/bash

# Files needed
pwd=`pwd`
. $pwd/unifi-api.sh

# Generation settings

uniemail=$1
uniusername=$2
unipassword=$3

#login to the controller
unifi_login >/dev/null
#create admin + grep accountID of just created read-only user
uniuser=`unifi_create_admin $uniemail $uniusername $unipassword | tr ':' '\n' | tail -1 | cut -d '"' -f 2`
#grant superadmin permissions to the just created user
unifi_grant_superadmin $uniuser
#logoff
unifi_logout
