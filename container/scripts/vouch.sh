#!/bin/bash

SELECTOR=$1

ls -l /

cat /templates/paste.ini | envsubst > /etc/vouch/paste.ini
cat /templates/$SELECTOR.conf | envsubst > /etc/vouch/$SELECTOR.conf

/vouch/vouch.py --config /etc/vouch/$SELECTOR.conf
