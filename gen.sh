#!/bin/bash

# Files needed
pwd=`pwd`
. $pwd/unifi-api.sh

# Generation settings
time=60 # Voucher time limit (minutes)
amount=15 # New vouchers to generate

# HTML Settings
line1="WiFi Voucher"
line2="Valid for 60 minutes"

# Generate vouchers
unifi_login
voucherID=`unifi_create_voucher $time $amount $note`
unifi_get_vouchers $voucherID > vouchers.tmp
unifi_logout

vouchers=`awk -F"[,:]" '{for(i=1;i<=NF;i++){if($i~/code\042/){print $(i+1)} } }' vouchers.tmp | sed 's/\"//g'`

# Build HTML
if [ -e vouchers.html ]; then
  echo "Removing old vouchers."
  rm vouchers.html
fi

echo '<html><head><link rel="stylesheet" href="style.css" /></head><body>' >> vouchers.html

for code in $vouchers
do
    line3=${code:0:5}" "${code:5:10}
    html='<div class="voucher"><div class="line1">'$line1'</div><div class="line2">'$line2'</div><div class="line3">'$line3'</div></div>'
    echo $html >> vouchers.html
done

echo "</body></html>" >> vouchers.html

# Remove tmp
if [ -e vouchers.tmp ]; then
  echo "Removing vouchers tmp file."
  rm vouchers.tmp
fi
