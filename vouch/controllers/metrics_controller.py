
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
from datetime import datetime, timezone
from dateutil import parser
from firkinize.configstore.consul import Consul


g_ca_cert_refresh_needed = Gauge('refresh_needed', 'Is CA cert refresh needed?')
g_ca_cert_expiry_time = Gauge('cert_expiry_time', 'Time in seconds till CA cert expires')
g_host_signing_token_expiry = Gauge('vouch_host_signing_token_expiry', 'Time in seconds till host signing token expires')


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(threadName)s - '
                           '%(levelname)s - %(message)s')
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
        config_url = os.environ.get('CONSUL_HTTP_ADDR', None)
        token = os.environ.get('CONSUL_HTTP_TOKEN', None)
        self.consul = Consul(config_url, token=token)
    
    def get_host_signing_token_expiry(self):
        current_time = time.time()
    
        try:
            vault_url = self.consul.kv_get(f'customers/{self.customer_uuid}/vouch/vault/url')
            host_signing_token = self.consul.kv_get(f'customers/{self.customer_uuid}/vouch/vault/host_signing_token')

            headers = {'X-Vault-Token': host_signing_token}

            LOG.info("Sending request to Vault token lookup-self API...")
            response = requests.get(f'{vault_url}/v1/auth/token/lookup-self', headers=headers)

            if response.status_code != 200:
                LOG.error(f"Vault token lookup failed: {response.status_code}, {response.text}")
                return None

            token_info = response.json()
            expire_str = token_info['data'].get('expire_time')

            if expire_str:
                expire_time = parser.isoparse(expire_str)
                current_time = datetime.now(timezone.utc)
                ttl_seconds = int((expire_time - current_time).total_seconds())
                self.host_signing_token_expiry = ttl_seconds
                self.host_signing_token_last_update_time = current_time
                LOG.info(f"Parsed expire time: {expire_time}")
                self.host_signing_token_last_update_time = current_time
            else:
                LOG.info("expire_time not found in Vault response.")

        except Exception as e:
                LOG.error(f"Error while fetching host signing token expiry: {e}")
                return None

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
