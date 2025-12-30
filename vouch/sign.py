# pylint: disable=too-few-public-methods

import base64
import json
import logging
import random
import requests
import string

from sanic import Sanic, response
from sanic.exceptions import SanicException
from sanic.log import logger

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.backends import default_backend

from kubernetes import client as kclient
from kubernetes import config as kconfig

from common_cert import get_latest_ca_cert, sign_csr, set_logger

LOG = logging.getLogger(__name__)
set_logger(LOG.info)

# return the root CA
def get_ca_data():

    latest_ca, _, version = get_latest_ca_cert(format='pem')

    reply = {}
    reply['revocation_time'] = 0
    reply['revocation_time_rfc3339'] = ''
    reply['certificate'] = latest_ca

    return reply

# replace the root CA
def refresh_ca_data():

    kconfig.load_kube_config()
    v1 = kclient.CoreV1Api()
    coa = kclient.CustomObjectsApi()

    latest_ca, _, version = get_latest_ca_cert()
    new_version = version + 1

    new_ca_name = 'v%d-ca' % new_version
    _, _, cert = create_new_ca(new_ca_name)

    reply = {}
    reply['certificate'] = cert

    return reply


def get_current_ca(request):
        """
        Get the CA cert of the currently configured CA
        """

        LOG.info('Fetching current ca certificate')
        try:
            reply = get_ca_data()
            LOG.info('status: 200')
            return response.json(reply)
        except requests.HTTPError as e:
            LOG.info('status: %s', e.response.status_code)
            raise SanicException("Could not fetch CA certs from kubernetes", status_code=e.response.status_code)

def generate_new_ca_root_cert(request):
        """
        Generate a new CA root certificate. Returns the old one and the new one.
        """

        resp_json = {}

        LOG.info('Refreshing ca certificate')
        try:
            old_cert_data = get_ca_data()
            resp_json['previous'] = json.dumps(old_cert_data)
            new_cert_data = refresh_ca_data()
            resp_json['new'] = json.dumps(new_cert_data)
            LOG.info('status: 200')
            return response.json(resp_json)
        except requests.HTTPError as e:
            LOG.info('status: %s', e.response.status_code)
            LOG.info('response json: %s', e.response.json())
            raise SanicException("Unable to refresh CA certificate", status_code=e.response.status_code)


def sanitize_and_unique(prefix, cert_name):

    if not cert_name:
        raise Exception('illegal for certificate name: ""')

    cert_name = cert_name.lower()

    # 110,075,314,176 possibilities in eight lowercase letters
    new_cert_name = prefix + '-' + ''.join(random.choices(string.ascii_lowercase, k=8)) + "--"

    for c in cert_name:
        if (c >= 'a' and c <= 'z') or (c >= '0' and c <= '9'):
            pass
        else:
            c = '-'
        new_cert_name += c

    if new_cert_name.endswith("-"):
        # only a crazy person would end a hostname with a special character. And this would
        # create an illegal name under Kubernetes. Apply a French cinematic solution.
        new_cert_name += "fin"

    return new_cert_name


def sign_cert(request):

    j = request.json

    if 'csr' not in j:
        raise SanicException("Signing request must contain a CSR", status_code=400)

    if 'private_key' not in j:
        raise SanicException("Signing request must contain a private_key. cert-manager requirement.", status_code=400)

    csr_parsed  = x509.load_pem_x509_csr(str(j['csr']).encode('utf-8'), default_backend())
    logger.info(f'Received CSR "{j["csr"]}", subject = "{csr_parsed.subject}"')

    cert_name = None
    try:
        common_name_attr = csr_parsed.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0]
        common_name_string = common_name_attr.value
        logger.info(f'Subject Common Name: {common_name_string}')
        cert_name = common_name_string
    except Exception as e:
        logger.info(f'error extracting CN: {e}')

    if not cert_name:
        raise Exception("cannot have an empty common name")

    # should this be overridden by a provided common_name parameter outside the CSR?
    cert_name = sanitize_and_unique('host', cert_name)

    common_name = j.get('common_name', None)
    ip_sans = j.get('ip_sans', [])
    alt_names = j.get('alt_names', [])
    ttl = j.get("ttl", [])

    logger.info(f'signing CSR {cert_name}')
    cert = sign_csr(cert_name, j['csr'], j['private_key'], ip_sans, alt_names, ttl)
    logger.info(f'Generated cert: {cert}')

    issuing_ca = ""
    try:
        issuing_ca, _, _ = get_latest_ca_cert(format='pem')
    except Exception as e:
        logger.info('failed getting issuing_ca: {e}')

    if type(cert) == bytes:
        cert = cert.decode()
    if type(issuing_ca) == bytes:
        issuing_ca = issuing_ca.decode()

    reply = { "certificate": cert, "issuing_ca": issuing_ca }
    logger.info(f'reply: {reply}')

    return response.json(reply)
