#!/bin/bash

VAULT_URL=$(curl --header "X-Consul-Token: $CONSUL_HTTP_TOKEN" $CONSUL_HTTP_ADDR/v1/kv/customers/$CUSTOMER_ID/regions/$REGION_ID/services/vouch/vault/url?raw 2>/dev/null)
VAULT_TOKEN=$(grep vault_token /etc/vouch/vouch-keystone.conf | awk '{ print $2 }')

TOKEN_HEALTH_STATUS=$(curl -o /dev/null -s -w "%{http_code}\n" --header "X-Vault-Token: $VAULT_TOKEN" $VAULT_URL/v1/auth/token/lookup-self)

if [ $TOKEN_HEALTH_STATUS != "200" ]; then
	echo "Service is not healthy, received $TOKEN_HEALTH_STATUS" > /proc/1/fd/1
	exit 1
fi

exit 0
