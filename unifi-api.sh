#!/bin/sh

# Unifi connection infomation
username=admin
password=PASSWORD
baseurl=https://CONTROLLERURL:8443

cookie=/tmp/unifi_cookie

curl_cmd="curl --silent --cookie ${cookie} --cookie-jar ${cookie} --insecure "

unifi_requires() {
    if [ -z "$username" -o -z "$password" -o -z "$baseurl" ] ; then
        echo "Error! please define required env vars before including unifi_sh. E.g. "
        echo ""
        echo "username=ubnt"
        echo "password=ubnt"
        echo "baseurl=http://unifi:8443"
        echo ""
        exit -1
    fi
}

unifi_login() {
    # authenticate against unifi controller
    ${curl_cmd} --data "login=login" --data "username=$username" --data "password=$password" $baseurl/login
}

unifi_logout() {
    # logout
    ${curl_cmd} $baseurl/logout
}

unifi_authorize_guest() {
    if [ $# -lt 2 ] ; then
        echo "Usage: $0 <mac> <minutes>"
        exit -1
    fi

    mac=$1
    minutes=$2

	${curl_cmd} --data "json={'cmd':'authorize-guest', 'mac':'${mac}', 'minutes':${minutes}}" $baseurl/api/cmd/stamgr
}

unifi_reconnect_sta() {
    if [ $# -lt 1 ] ; then
        echo "Usage: $0 <mac>"
        exit -1
    fi

    mac=$1

    ${curl_cmd} --data "json={'cmd':'kick-sta', 'mac':'${mac}'}" $baseurl/api/cmd/stamgr
}


unifi_block_sta() {
    if [ $# -lt 1 ] ; then
        echo "Usage: $0 <mac>"
        exit -1
    fi

    mac=$1

    ${curl_cmd} --data "json={'cmd':'block-sta', 'mac':'${mac}'}" $baseurl/api/cmd/stamgr
}

unifi_list_sta() {
    ${curl_cmd} --data "json={}" $baseurl/api/stat/sta
}

unifi_backup() {
    if [ "$1" = "" ]; then
        output=unifi-backup.unf # or `date +%Y%m%d`.unf
    else
        output=$1
    fi

    # ask controller to do a backup, response contains the path to the backup file
    path=`$curl_cmd --data "json={'cmd':'backup'}" $baseurl/api/cmd/system | sed -n 's/.*\(\/dl.*unf\).*/\1/p'`

    # download the backup to the destinated output file
    $curl_cmd $baseurl$path -o $output
}

unifi_create_voucher() {
    if [ $# -lt 2 ] ; then
        echo "Usage: $0 <minutes> <n> [note]"
        exit -1
    fi
    minutes=$1
    n=$2
    [ "$3" != "" ] && note=", 'note':'$3' "
    token=`${curl_cmd} --data "json={'cmd':'create-voucher','expire':${minutes},'n':$n $note}" $baseurl/api/cmd/hotspot \
    	| sed -e 's/.*"create_time"\s*:\s*\([0-9]\+\).*/\1/'`
    echo $token
}

unifi_get_vouchers() {
    if [ $# -lt 1 ] ; then
        echo "Usage: $0 <token>"
        exit -1
    fi
    token=$1
    ${curl_cmd} --data "json={'create_time':${token}}" $baseurl/api/stat/voucher
}

unifi_requires

