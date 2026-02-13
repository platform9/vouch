#!/bin/bash

ls -l /

cat /templates/paste.ini | envsubst > /etc/vouch/paste.ini
cat /templates/vouch-keystone.conf | envsubst > /etc/vouch/vouch-keystone.conf
cat /templates/vouch-noauth.conf | envsubst > /etc/vouch/vouch-noauth.conf

/usr/local/bin/vouch --config /etc/vouch/vouch-keystone.conf
