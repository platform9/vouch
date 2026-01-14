
import base64
import logging
import os
import re
import time

from cryptography import x509
from cryptography.hazmat.backends import default_backend

from kubernetes import client as kclient
from kubernetes import config as kconfig
from kubernetes.dynamic import DynamicClient

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
        return None, None

    if not secrets or not secrets.items:
        return None, None

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
        return c, latest_ca_version
    else:
        return None, None

def create_new_ca(name):

    try:
        kconfig.load_kube_config()
    except kconfig.ConfigException:
        kconfig.load_incluster_config()

    v1 = kclient.CoreV1Api()
    dyn_client = DynamicClient(kclient.ApiClient())

    issuer_api = dyn_client.resources.get(api_version='cert-manager.io/v1', kind='Issuer')
    certificate_api = dyn_client.resources.get(api_version='cert-manager.io/v1', kind='Certificate')

    new_issuer = {
            "apiVersion": "cert-manager.io/v1",
            "kind": "Issuer",
            "metadata": {
                "name": name + "-issuer",
                "namespace": namespace,
            },
            "spec": {
                "selfSigned": {}
            }
        }
        
    new_issuer_response = issuer_api.create(body=new_issuer)
    print(new_issuer_response)

    secret_name = name + '-secret'

    new_cert = {
            "apiVersion": "cert-manager.io/v1",
            "kind": "Certificate",
            "metadata": {
                "name": name + "-cert",
                "namespace": namespace,
            },
            "spec": {
                "commonName": name + "-cert",
                "isCA": True,
                "issuerRef": {
                    "group": "cert-manager.io",
                    "kind": "Issuer",
                    "name": name + "-issuer",
                },
                "privateKey": {
                    "algorithm": "ECDSA",
                    "size": 256,
                },
                "secretName": secret_name,
                "subject": {
                    "organizationalUnits": [ 'Starches' ],
                    "organizations": [ 'Rutabega Inc.' ],
                }
            }
        }

    new_cert_response = certificate_api.create(body=new_cert)
    print(new_cert_response)

    TIMEOUT=120

    start = int(time.time())
    while True:
        print('checking if new CA cert "%s" is ready' % secret_name)
        secret = None
        try:
            secret = v1.read_namespaced_secret(secret_name, namespace)
        except:
            pass
        if secret and secret.data and "ca.crt" in secret.data:
            data_b64 = secret.data["ca.crt"]
            if len(data_b64) > 10:
                cert = base64.b64decode(data_b64).decode()
                return cert
        now = int(time.time())
        if now - start > TIMEOUT:
            raise("failed to obtain new CA certificate")
        time.sleep(1)

func sign_csr(csr, common_name, ip_sans, alt_names, ttl):

    pass


"""
signing role:

'key_bits': 2048,
'allow_any_name': True,
'use_csr_sans': False,
'use_csr_common_name': False
"""
