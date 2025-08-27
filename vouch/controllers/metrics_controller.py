
import os
import logging
import pecan
import time
import requests
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from pecan import expose
from pecan.rest import RestController

from vouch.conf import CONF
from vaultlib.ca import VaultCA
from prometheus_client import generate_latest, Gauge
from bin.common import parse


g_ca_cert_refresh_needed = Gauge('refresh_needed', 'Is CA cert refresh needed?')
g_ca_cert_expiry_time = Gauge('cert_expiry_time', 'Time in seconds till CA cert expires')
g_host_signing_token_expiry = Gauge('host_signing_token_expiry', 'Time in seconds till host signing token expires')


LOG = logging.getLogger(__name__)

def query_vault(vault):
    resp = vault.get_ca()
    cert = resp.json()['data']['certificate']
    c=x509.load_pem_x509_certificate(cert.encode('utf-8'),default_backend())
    return c

class  MetricsController(RestController):
    def __init__(self):
        self._vault = VaultCA(
            CONF['vault_addr'],
            CONF['vault_token'],
            CONF['ca_name'],
            CONF['ca_common_name'],
        )
        self.last_update_time = time.time()
        cert = query_vault(self._vault)
        self.cert_expiration_time = cert.not_valid_after

        # For querying host signing token expiry
        self.vault_token = CONF['vault_token']
        self.host_signing_token_expiry = None
        self.host_signing_token_last_update_time = time.time()
        self.customer_uuid = os.environ['CUSTOMER_ID']
        _, self.consul = parse()

    
    def get_host_signing_token_expiry(self):
        current_time = time.time()
    
        if ((current_time - self.host_signing_token_last_update_time) > CONF['vault_query_interval']):
            vault_url = self.consul.kv_get(f'customers/{self.customer_uuid}/vouch/vault/url')
            host_signing_token = self.consul.kv_get(f'customers/{self.customer_uuid}/vouch/vault/host_signing_token')

            headers = {'X-Vault-Token': self.vault_token}  # Management token
            payload = {"token": host_signing_token}

            response = requests.post(f'{vault_url}/v1/auth/token/lookup', headers=headers, json=payload)
            if response.status_code != 200:
                raise Exception(f"Failed to lookup token: {response.text}")

            token_info = response.json()
            expire_time = token_info['data'].get('expire_time')  # e.g. "2025-08-30T12:34:56Z"

            self.host_signing_token_expiry = expire_time
            self.host_signing_token_last_update_time = current_time

            return self.host_signing_token_expiry


    def get_cert_expiration_time(self):
        current_time = time.time()
        if ((current_time - self.last_update_time) > CONF['vault_query_interval']):
            cert = query_vault(self._vault)
            self.cert_expiration_time = cert.not_valid_after
            self.last_update_time = current_time
        return self.cert_expiration_time

    @expose(content_type='text/plain')
    def get(self):
        """
        GET /metrics
        """
        try:
            self.get_cert_expiration_time()
            host_signing_token_expiry = self.get_host_signing_token_expiry()
            ca_cert_expiry_time = time.mktime(self.cert_expiration_time.timetuple())
            current_time = time.time()
            g_ca_cert_expiry_time.set(int(ca_cert_expiry_time))
            g_host_signing_token_expiry.set(host_signing_token_expiry)
            if ca_cert_expiry_time - current_time < CONF['refresh_period']:
                g_ca_cert_refresh_needed.set(1)
            else:
                g_ca_cert_refresh_needed.set(0)
        except requests.HTTPError as e:
            pecan.response.status = e.response.status_code
            pecan.response.text = e.response.text()
            return pecan.response
        else:
            return generate_latest()
