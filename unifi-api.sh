#!/bin/sh

# Controller connection settings
username=ubnt
password=ubnt
baseurl=https://unifi:8443
site=default # site=692ccbzc can be found from the dashboard URL: https://unifi.example.com/manage/site/692ccbzc/dashboard

[ -f ./unifi_sh_env ] && . ./unifi_sh_env

cookie=unifi_cookie_tmp

curl_cmd="curl --tlsv1 --silent --cookie ${cookie} --cookie-jar ${cookie} --insecure "

named_args_to_payload() {
    payload=""
    for a in "$@" ; do
        if [ "${a##*=*}" = "" ] ; then
            k=`echo $a | cut -d = -f 1`
            v=`echo $a | cut -d = -f 2`
            payload="${payload}, '$k':'$v'"
        fi
    done
    echo ${payload}
}

unifi_requires() {
    if [ -z "$username" -o -z "$password" -o -z "$baseurl" -o -z "$site" ] ; then
        echo "Error! please define required env vars before including unifi_sh. E.g. "
        echo ""
        echo "export username=ubnt"
        echo "export password=ubnt"
        echo "export baseurl=https://localhost:8443"
        echo "export site=default"
        echo ""
        return
    fi
}

unifi_login() {
    # authenticate against unifi controller
    ${curl_cmd} --data "{'username':'$username', 'password':'$password'}" $baseurl/api/login
}

unifi_logout() {
    # logout
    ${curl_cmd} $baseurl/logout
    rm $cookie
}

unifi_api() {
    if [ $# -lt 1 ] ; then
        echo "Usage: $0 <uri> [json]"
        echo "    uri example /stat/sta "
        return
    fi
    uri=$1
    shift
    [ "${uri:0:1}" != "/" ] && uri="/$uri"
    json="$@"
    [ "$json" = "" ] && json="{}"
    ${curl_cmd} --data "$json" $baseurl/api/s/$site$uri
}

# cmd/stamgr
# authorize-guest(mac, minutes, [up=kbps, down=kbps, bytes=MB])
unifi_authorize_guest() {
    if [ $# -lt 2 ] ; then
        echo "Usage: $0 <mac> <minutes> [up=kbps] [down=kbps] [bytes=MB] [ap_mac=mac]"
        return
    fi

    mac=$1
    minutes=$2
    other_payload=`named_args_to_payload "$@"`

    ${curl_cmd} --data "json={'cmd':'authorize-guest', 'mac':'${mac}', 'minutes':${minutes}${other_payload}}" $baseurl/api/s/$site/cmd/stamgr
}

# cmd/stamgr
# unauthorize-guest(mac)
unifi_unauthorize_guest() {
    if [ $# -lt 1 ] ; then
        echo "Usage: $0 <mac>"
        return
    fi

    mac=$1

    ${curl_cmd} --data "json={'cmd':'unauthorize-guest', 'mac':'${mac}'}" $baseurl/api/s/$site/cmd/stamgr
}

# cmd/stamgr
# kick-sta(mac)
unifi_reconnect_sta() {
    if [ $# -lt 1 ] ; then
        echo "Usage: $0 <mac>"
        return
    fi

    mac=$1

    ${curl_cmd} --data "json={'cmd':'kick-sta', 'mac':'${mac}'}" $baseurl/api/s/$site/cmd/stamgr
}

# cmd/stamgr
# block-sta(mac)
unifi_block_sta() {
    if [ $# -lt 1 ] ; then
        echo "Usage: $0 <mac>"
        return
    fi

    mac=$1

    ${curl_cmd} --data "json={'cmd':'block-sta', 'mac':'${mac}'}" $baseurl/api/s/$site/cmd/stamgr
}

unifi_backup() {
    if [ "$1" = "" ]; then
        output=unifi-backup.unf # or `date +%Y%m%d`.unf
    else
        output=$1
    fi

    # ask controller to do a backup, response contains the path to the backup file
    path=`$curl_cmd --data "json={'cmd':'backup'}" $baseurl/api/s/$site/cmd/system | sed -n 's/.*\(\/dl.*unf\).*/\1/p'`

    # download the backup to the destinated output file
    $curl_cmd $baseurl$path -o $output
}

# cmd/hotspot
# create-voucher(expires, n, [note=notes, up=kbps, down=kbps, bytes=MB])
# @returns create_time
unifi_create_voucher() {
    if [ $# -lt 2 ] ; then
        echo "Usage: $0 <minutes> <n> [note=notes] [up=kbps] [down=kbps] [bytes=MB]"
        return
    fi
    minutes=$1
    n=$2
    other_payload=`named_args_to_payload "$@"`
    token=`${curl_cmd} --data "json={'cmd':'create-voucher','expire':${minutes},'n':$n ${other_payload}}" $baseurl/api/s/$site/cmd/hotspot \
        | sed -e 's/.*"create_time"\s*:\s*\([0-9]\+\).*/\1/'`
    echo "token=$token"
    if [ "$token" != "" ] ; then
        ${curl_cmd} --data "json={'create_time':${token}}" $baseurl/api/s/$site/stat/voucher
    fi
}

# stat/voucher
# query(create_time)
unifi_get_vouchers() {
    set -x
    if [ $# -lt 0 ] ; then
        echo "Usage: $0 [token]"
        return
    fi
    token=$1
    [ "$token" != "" ] && other_payload="'create_time':${token}"
    ${curl_cmd} --data "json={${other_payload}}" $baseurl/api/s/$site/stat/voucher
    echo ${curl_cmd} --data "json={${other_payload}}" $baseurl/api/s/$site/stat/voucher
}

# delete-voucher(id)
unifi_delete_voucher() {
    if [ $# -lt 1 ] ; then
        echo "Usage: $0 <id>"
        return
    fi
    id=$1
    ${curl_cmd} --data "json={'cmd':'delete-voucher','_id':'${id}'}" $baseurl/api/s/$site/cmd/hotspot
}

# stat/sta
unifi_list_sta() {
    ${curl_cmd} --data "json={}" $baseurl/api/s/$site/stat/sta
}


unifi_requires
