
import base64
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

from kubernetes import client as kclient
from kubernetes import config as kconfig

# Exporter gauges
g_ca_cert_refresh_needed = Gauge('refresh_needed', 'Is CA cert refresh needed?')
g_ca_cert_expiry_time = Gauge('cert_expiry_time', 'Time in seconds till CA cert expires')

LOG = logging.getLogger(__name__)

def get_latest_ca_cert():

    LOG.info('get_latest_ca_cert')

    try:
        kconfig.load_kube_config()
    except kconfig.ConfigException:
        kconfig.load_incluster_config()

    v1 = kclient.CoreV1Api()
    namespace = os.environ["NAMESPACE"]

    latest_ca_cert = None
    latest_ca_version = None

    try:
        secrets = v1.list_namespaced_secret(namespace=namespace)
    except:
        LOG.error('could not fetch CA certs from kubernetes:', e)
        return None

    if not secrets or not secrets.items:
        return None

    pattern = '^v(\d+)-ca-secret$'
    for secret in secrets.items:
        match = re.search(pattern, secret.metadata.name)
        if match:
            version = int(match.group(1))
            if not latest_ca_version or latest_ca_version < version:
                data_b64 = secrets.data["ca.crt"]
                latest_ca_cert = str(base64.b64decode(data_b64))
                latest_ca_version = version

    if latest_ca_cert:
        c = x509.load_pem_x509_certificate(latest_ca_cert.encode('utf-8'),default_backend())
        return c
    else:
        return None

def query_vault(vault):
    resp = vault.get_ca()
    cert = resp.json()['data']['certificate']
    c=x509.load_pem_x509_certificate(cert.encode('utf-8'),default_backend())
    return c
    
class  MetricsController(RestController):
    def __init__(self):
        self.last_update_time = time.time()
        cert = get_latest_ca_cert()
        self.cert_expiration_time = cert.not_valid_after

    def get_cert_expiration_time(self):
        current_time = time.time()
        if ((current_time - self.last_update_time) > CONF['vault_query_interval']):
            cert = get_latest_ca_cert()
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
            ca_cert_expiry_time = time.mktime(self.cert_expiration_time.timetuple())
            current_time = time.time()
            g_ca_cert_expiry_time.set(int(ca_cert_expiry_time))
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
