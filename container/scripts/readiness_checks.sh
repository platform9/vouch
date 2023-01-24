#!/bin/bash

VAULT_URL=$(curl --header "X-Consul-Token: $CONSUL_HTTP_TOKEN" $CONSUL_HTTP_ADDR/v1/kv/customers/$CUSTOMER_ID/vouch/vault/url?raw 2>/dev/null)
VAULT_TOKEN=$(curl --header "X-Consul-Token: $CONSUL_HTTP_TOKEN" $CONSUL_HTTP_ADDR/v1/kv/customers/$CUSTOMER_ID/vouch/vault/host_signing_token?raw 2>/dev/null)

TOKEN_HEALTH_STATUS=$(curl -o /dev/null -s -w "%{http_code}\n" --header "X-Vault-Token: $VAULT_TOKEN" $VAULT_URL/v1/auth/token/lookup-self)

if [ $TOKEN_HEALTH_STATUS != "200" ]; then
	exit 1
fi

exit 0