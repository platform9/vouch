
import base64
import datetime
import logging
import os
import re
import subprocess
import time

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption

from kubernetes import client as kclient
from kubernetes import config as kconfig
from kubernetes.dynamic import DynamicClient

LOG = logging.getLogger(__name__)


def set_logger(new_logger):
    LOG = new_logger


def config_kubernetes():

    try:
        kconfig.load_kube_config()
    except kconfig.ConfigException:
        kconfig.load_incluster_config()

    v1 = kclient.CoreV1Api()
    certs_api = kclient.CertificatesV1Api()
    dyn_client = DynamicClient(kclient.ApiClient())

    return v1, certs_api, dyn_client


def generate_csr(common_name, alt_names, ttl):

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, common_name)
    ])

    key_usage_ext = x509.KeyUsage(
        digital_signature=True,
        content_commitment=False,
        key_encipherment=True,
        data_encipherment=False,
        key_agreement=False,
        key_cert_sign=False,
        crl_sign=False,
        encipher_only=False,
        decipher_only=False,
    )

    extended_key_usage_ext = x509.ExtendedKeyUsage([
        ExtendedKeyUsageOID.CLIENT_AUTH,
        ExtendedKeyUsageOID.SERVER_AUTH,
    ])

    san_ext = x509.SubjectAlternativeName([ x509.DNSName(alt) for alt in alt_names ])

    csr = x509.CertificateSigningRequestBuilder().subject_name(subject)

    # csr = csr.add_extension(key_usage_ext, critical=False)
    csr = csr.add_extension(extended_key_usage_ext, critical=False)
    csr = csr.add_extension(san_ext, critical=False)

    signed_csr = csr.sign(private_key, hashes.SHA256())

    csr_pem = signed_csr.public_bytes(Encoding.PEM)
    private_key_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())

    return private_key_pem, csr_pem


def get_latest_ca_cert(format='cert'):

    LOG.info('get_latest_ca_cert')

    v1, _, _ = config_kubernetes()
    namespace = os.environ["NAMESPACE"]

    latest_ca_cert = None
    latest_ca_version = None

    try:
        secrets = v1.list_namespaced_secret(namespace=namespace)
    except Exception as e:
        LOG.error('could not fetch CA certs from kubernetes:', e)
        return None, None, None

    if not secrets or not secrets.items:
        return None, None, None

    pattern = '^v(\d+)-ca-secret$'
    for secret in secrets.items:
        match = re.search(pattern, secret.metadata.name)
        if match:
            version = int(match.group(1))
            LOG.info("%s: version: %d" % (secret.metadata.name, version))
            if not latest_ca_version or latest_ca_version < version and secret.data and 'ca.crt' in secret.data:
                cert_b64 = secret.data["ca.crt"]
                key_b64 = secret.data["tls.key"]
                latest_ca_cert = base64.b64decode(cert_b64)
                latest_ca_key = base64.b64decode(key_b64)
                latest_ca_version = version

    if latest_ca_cert:
        pem = latest_ca_cert.decode()
        LOG.info(pem)
        if format == 'cert':
            c = x509.load_pem_x509_certificate(bytes(pem.encode("utf-8")),default_backend())
        elif format == 'pem':
            c = str(latest_ca_cert.decode())
        return c, latest_ca_key, latest_ca_version
    else:
        return None, None, None


def wait_key_from_secret(v1, secret_name, namespace_name, key):

    TIMEOUT=120

    start = int(time.time())
    while True:
        LOG.info('checking if new CA cert "%s" is ready' % secret_name)
        secret = None
        try:
            secret = v1.read_namespaced_secret(secret_name, namespace_name)
        except Exception as e:
            LOG.info('failed to read secret "%s" in namespace "%s": %s', secret_name, namespace_name, e)
            pass
        if secret and secret.data:
            if key in secret.data:
                data_b64 = secret.data[key]
                if len(data_b64) > 10:
                    cert = base64.b64decode(data_b64).decode("utf-8")
                    LOG.info('success')
                    return cert
                else:
                    LOG.info('key "%s" was found but it is much too short' % key)
            else:
                LOG.info('secret does not yet have "%s" present' % key)
        now = int(time.time())
        if now - start > TIMEOUT:
            raise("failed to obtain new CA certificate after %d seconds" % TIMEOUT)
        time.sleep(3)

def create_new_ca(name):

    # SHOULD BE ca_ttl=26280h

    namespace = os.environ["NAMESPACE"]

    v1, _, dyn_client  = config_kubernetes()

    issuer_api = dyn_client.resources.get(api_version='cert-manager.io/v1', kind='Issuer')
    certificate_api = dyn_client.resources.get(api_version='cert-manager.io/v1', kind='Certificate')

    issuers = issuer_api.get(namespace=namespace)

    for issuer in issuers.items:
        LOG.info("ISSUER: %s" % issuer['metadata']['name'])

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
    LOG.info(new_issuer_response)

    secret_name = name + '-secret'
    cert_name = name + '-cert'

    new_cert = {
            "apiVersion": "cert-manager.io/v1",
            "kind": "Certificate",
            "metadata": {
                "name": cert_name,
                "namespace": namespace,
            },
            "spec": {
                "commonName": cert_name,
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
    LOG.info(new_cert_response)

    cert = wait_key_from_secret(v1, secret_name, namespace, "ca.crt")
    return cert




"""
signing role:

'key_bits': 2048,
'allow_any_name': True,
'use_csr_sans': False,
'use_csr_common_name': False
"""


def get_wanted_or_max_ttl(ttl):

    if not ttl:
        # force maximum if none given
        ttl = 999999

    ca, _, latest_version = get_latest_ca_cert()

    if isinstance(ttl, str):
        if ttl.endswith('h'):
            ttl = ttl[:-1]
    wanted_ttl = int(ttl)

    not_after = ca.not_valid_after
    now = datetime.datetime.utcnow()
    max_possible_ttl = ((not_after - now).total_seconds() / 60 / 60) - 1

    if max_possible_ttl < wanted_ttl:
        final_ttl = max_possible_ttl
    else:
        final_ttl = wanted_ttl

    LOG.info('wanted cert ttl %sh, ca ttl %sh, using %sh', ttl, max_possible_ttl, final_ttl)
    return '{}h'.format(final_ttl), latest_version


def get_all_certs():

    # returns a list of certs in the layout we previously used in Consul

    LOG.info('get_all_certs')

    v1, _, _ = config_kubernetes()
    namespace = os.environ["NAMESPACE"]

    latest_ca_version = None
    data = {}

    try:
        secrets = v1.list_namespaced_secret(namespace=namespace)
    except Exception as e:
        LOG.error('error accessing secrets to fetch versioned certs from Kubernetes:', e)
        return data

    if not secrets or not secrets.items:
        LOG.error('no versioned certs were found in the Kubernetes secrets')
        return data

    pattern = '^v(\d+)-(.*)-secret$'
    for secret in secrets.items:
        match = re.search(pattern, secret.metadata.name)
        if match:
            version = int(match.group(1))
            cert_name = match.group(2)

            version_name = 'v' + str(version)
            if version_name not in data:
                data[version_name] = {}

            if cert_name == 'ca':
                cert_b64 = secret.data["ca.crt"]
            else:
                cert_b64 = secret.data["tls.crt"]
            key_b64 = secret.data['tls.key']

            cert = str(base64.b64decode(cert_b64))
            key = str(base64.b64decode(key_b64))
            data[version_name][cert_name] = { 'cert': cert, 'key': key }

            if not latest_ca_version or latest_ca_version < version:
                latest_ca_version = version

    if latest_ca_version:
        data['current_version'] = 'v' + str(latest_ca_version)

    return data


def create_cert(cert_name, common_name, alt_names, ttl='13140h'):

    ttl, latest_version = get_wanted_or_max_ttl(ttl)

    namespace = os.environ["NAMESPACE"]

    v1, kcerts_api, dyn_client = config_kubernetes()

    private_key, csr = generate_csr(common_name, alt_names, ttl)

    cert = sign_csr(cert_name, csr, private_key)
    return private_key, cert


def sign_csr(cert_name, csr, private_key, ip_sans=None, alt_names=None, ttl=None):

    v1, kcerts_api, dyn_client = config_kubernetes()

    namespace = os.environ["NAMESPACE"]
    secret_name = cert_name + '-key'

    annotations = {
        "experimental.cert-manager.io/private-key-secret-name": secret_name,
        "platform9/certificate-regime": "ikr"
    }

    LOG.info(f'private_key: {private_key}')

    if type(private_key) == str:
        private_key = private_key.encode()
    private_key_b64 = base64.b64encode(private_key).decode('utf-8')

    pk_data = { "tls.key": private_key_b64 }

    # create a secret with the private key

    pk_annotations = {
        "cert-manager.io/allow-direct-injection": "true",
        "platform9/certificate-regime": "ikr"
    }
    pk_secret = kclient.V1Secret(
        metadata=kclient.V1ObjectMeta(
            name=secret_name,
            annotations=pk_annotations),
        type="Opaque",
        data=pk_data,
    )

    api_response = v1.create_namespaced_secret(namespace=namespace, body=pk_secret)
    # LOG.info(f'create secret response: {api_response}')

    ttl, latest_version = get_wanted_or_max_ttl(ttl)
    signer_name = 'issuers.cert-manager.io/' + namespace + '.' + 'v' + str(latest_version) + '-ca-issuer'

    usages = ['client auth', 'server auth']

    if alt_names:
        san_ext = x509.SubjectAlternativeName([ x509.DNSName(alt) for alt in alt_names ])
        csr = csr.add_extension(san_ext, critical=False)

    LOG.info(f'csr: {csr}')

    if type(csr) == str:
        csr = csr.encode()
    csr_b64 = base64.b64encode(csr).decode('utf-8')

    k8s_csr = kclient.V1CertificateSigningRequest(
        api_version="certificates.k8s.io/v1",
        kind="CertificateSigningRequest",
        metadata=kclient.V1ObjectMeta(name=cert_name, namespace=namespace, annotations=annotations),
        spec=kclient.V1CertificateSigningRequestSpec(
            request=csr_b64,
            signer_name=signer_name,
            usages=usages,
        )
    )

    LOG.info(f'k8s_csr: {k8s_csr}')

    response = kcerts_api.create_certificate_signing_request(body=k8s_csr)

    # LOG.info("k8s_csr response: %s", response)

    success = False
    for i in range(5):
        cmd = ['kubectl', 'certificate', 'approve', cert_name]
        LOG.info('running: ' + str(cmd))
        try:
            result = subprocess.run(cmd, capture_output=True, check=True)
            success = True
        except subprocess.CalledProcessError as e:
            print(f"kubectl command failed with return code {e.returncode}")
            print("kubectl stderr:", e.stderr)
        except FileNotFoundError:
            raise Exception("kubectl is not in the PATH")
        time.sleep(1+i)

    if not success:
        raise Exception("unable to approve certificate, please examine log")

    cert = None
    timeout = 120
    start = time.time()
    while True:
        LOG.info("checking if cert is ready")
        csr_body = kcerts_api.read_certificate_signing_request(name=cert_name)
        if csr_body.status.certificate is None:
            now = time.time()
            if now - start > timeout:
                raise(f'timed out waiting for certificate creation ({timeout} seconds)')
            time.sleep(5)
            continue
        cert = base64.b64decode(csr_body.status.certificate)
        break

    return cert
