#!/bin/sh

# Files needed
pwd=`pwd`
. $pwd/unifi-api.sh

# Generation settings
time=60
amount=15
note="TEST"

# Generate vouchers
unifi_login
voucherID=`unifi_create_voucher $time $amount $note`
unifi_get_vouchers $voucherID > vouchers.tmp
unifi_logout

vouchers=`awk -F"[,:]" '{for(i=1;i<=NF;i++){if($i~/code\042/){print $(i+1)} } }' vouchers.tmp | sed 's/\"//g'`

# HTML Settings
line1="COMPANY WiFi Voucher"
line2="60 minutes of use"

# Build HTML
if [ -e vouchers.html ]; then
  echo "Removing old vouchers."
  rm vouchers.html
fi

echo '<html><head><link rel="stylesheet" href="style.css" /></head><body>' >> vouchers.html

for code in $vouchers
do
    line3=$code
    html='<div class="voucher"><div class="line1">'$line1'</div><div class="line2">'$line2'</div><div class="line3">'$line3'</div></div>'
    echo $html >> vouchers.html
done

echo "</body></html>" >> vouchers.html

# Remove tmp
if [ -e vouchers.tmp ]; then
  echo "Removing vouchers tmp file."
  rm vouchers.tmp
fi
