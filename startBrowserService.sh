#!/bin/bash

# 
# to install place symlink to this file at...
# /home/pi/RetroPie/retropiemenu/startBrowserService.sh
#

/opt/retropie/supplementary/retropie-manager/rpmanager.sh --stop &>/dev/null

exec 5>&1
rpManager=$(/opt/retropie/supplementary/retropie-manager/rpmanager.sh --start | tee >(cat - >&5))

# port=${rpManager##t*port\ }
# port=${port%"."}

port=$(echo $rpManager | sed 's/.*port.//')

ipAddy="$(ip route get 8.8.8.8 2>/dev/null | awk '{print $NF; exit}')"

echo
echo Start a browser and navigate to
echo
echo "     $ipAddy:$port"
echo

sleep 10

