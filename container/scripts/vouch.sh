#!/bin/bash

ls -l /

cat /templates/paste.ini | envsubst > /etc/vouch/paste.ini
cat /templates/$APP.conf | envsubst > /etc/vouch/$APP.conf

while true; do
    echo "/vouch/vouch.py --config /etc/vouch/$APP.conf"
    /vouch/vouch.py --config /etc/vouch/$APP.conf
    echo vouch crashed! restarting
    sleep 15
done
