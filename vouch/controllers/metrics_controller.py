
import os
import logging
import pecan
import time
import calendar
import requests
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from pecan import expose
from pecan.rest import RestController

from vouch.conf import CONF
from vaultlib.ca import VaultCA
from prometheus_client import generate_latest, Gauge
from datetime import datetime
from firkinize.configstore.consul import Consul


g_ca_cert_refresh_needed = Gauge('refresh_needed', 'Is CA cert refresh needed?')
g_ca_cert_expiry_time = Gauge('cert_expiry_time', 'Time in seconds till CA cert expires')
g_host_signing_token_expiry = Gauge('host_signing_token_expiry', 'Time in seconds till host signing token expires')


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(threadName)s - '
                           '%(levelname)s - %(message)s')
LOG = logging.getLogger(__name__)

def write_debug(msg):
    with open("/tmp/vouch_debug.log", "a") as f:
        f.write(f"[{datetime.now()}] {msg}\n")

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

        write_debug(f"MetricsController initialized with customer ID: {self.customer_uuid}")

    
    def get_host_signing_token_expiry(self):
        current_time = time.time()
        write_debug("Fetching host signing token expiry...")
    
        try:
            write_debug("Cache expired or empty. Querying Consul for vault URL and token...")
            vault_url = self.consul.kv_get(f'customers/{self.customer_uuid}/vouch/vault/url')
            host_signing_token = self.consul.kv_get(f'customers/{self.customer_uuid}/vouch/vault/host_signing_token')

            write_debug(f"Vault URL: {vault_url}")
            write_debug(f"Host signing token: {host_signing_token[:5]}... (masked)")

            headers = {'X-Vault-Token': self.vault_token}
            payload = {"token": host_signing_token}

            write_debug("Sending request to Vault token lookup API...")
            response = requests.post(f'{vault_url}/v1/auth/token/lookup', headers=headers, json=payload)

            if response.status_code != 200:
                LOG.error(f"Vault token lookup failed: {response.status_code}, {response.text}")
                return None

            token_info = response.json()
            expire_time = token_info['data'].get('expire_time')
            write_debug(f"Expire time from Vault: {expire_time}")

            if expire_time:
                dt = datetime.strptime(expire_time, "%Y-%m-%dT%H:%M:%SZ")
                epoch_expire_time = calendar.timegm(dt.timetuple())
                self.host_signing_token_expiry = epoch_expire_time
                self.host_signing_token_last_update_time = current_time
                write_debug(f"Host signing token expiry (epoch): {epoch_expire_time}")
            else:
                write_debug("expire_time not found in Vault response.")

        except Exception as e:
                write_debug(f"Error while fetching host signing token expiry: {e}")
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
        write_debug("get /metrics called")

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
            write_debug("get /metricc set token gauges")
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
