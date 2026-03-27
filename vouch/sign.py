# pylint: disable=too-few-public-methods

import base64
import json
import logging
import requests

from sanic import Sanic, response
from sanic.exceptions import SanicException
from sanic.log import logger

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.backends import default_backend

from kubernetes import client as kclient
from kubernetes import config as kconfig

from cert_utils import get_latest_ca_cert, sign_csr


LOG = logging.getLogger(__name__)

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
    cert = create_new_ca(new_ca_name)

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


def sign_cert(request):

    j = request.json

    if 'csr' not in j:
        raise SanicException("Signing request must contain a CSR", status_code=400)

    if 'private_key' not in j:
        raise SanicException("Signing request must contain a private_key. cert-manager requirement.", status_code=400)

    csr_parsed  = x509.load_pem_x509_csr(str(j['csr']).encode('utf-8'), default_backend())
    logger.info(f'Received CSR "{j["csr"]}", subject = "{csr_parsed.subject}"')

    cert_name = 'doot-doot'
    try:
        common_name_attr = csr_parsed.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0]
        common_name_string = common_name_attr.value
        logger.info(f'Subject Common Name: {common_name_string}')
        cert_name = common_name_string
    except Exception as e:
        logger.info(f'error extracting CN: {e}')

    # TODO, make sure this is a legal kubernetes resource name
    # cert_name = sanitize(cert_name)

    common_name = j.get('common_name', None)
    ip_sans = j.get('ip_sans', [])
    alt_names = j.get('alt_names', [])
    ttl = j.get("ttl", [])

    logger.info('signing CSR {cert_name}')
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
