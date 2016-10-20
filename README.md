Generates UniFi vouchers using the controller API. CSS fully styleable and ready to print.

This script can be run from any NIX machine that can see the UniFi controller.

1. Download the repo using Git.
    git clone git://github.com/davidmaitland/unifi-voucher-generator.git

2. Edit the "unifi-api.sh" with your controller's Username, Password and URL.

3. Edit the "gen.sh" script with your own varibles.

4. Run the "gen.sh" script, which will connect to your controller, generate the keys and produce a vouchers.html ready to print.

Notes:
- CSS is in the "style.css" file.

Soon:
- Interactive command line.