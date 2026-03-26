# pylint: disable=too-few-public-methods

import base64
import json
import logging
import requests

from sanic import Sanic, response
from sanic.exceptions import SanicException
from sanic.log import logger

from cryptography import x509
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

    csr_parsed  = x509.load_pem_x509_csr(str(j['csr']).encode('utf-8'), default_backend())
    logger.info('Received CSR \'%s\', subject = %s', j['csr'], csr_parsed.subject)

    common_name = j.get('common_name', None)
    ip_sans = j.get('ip_sans', [])
    alt_names = j.get('alt_names', [])
    ttl = j.get("ttl", [])

    cert = sign_csr(j['csr'].encode(), common_name, ip_sans, alt_names, ttl)
    logger.info('Generated cert: %s' % cert)

"""
class CertController(RestController):
    def __init__(self):
        pass

    @expose('json')
    def post(self):
        # POST /v1/sign/cert
        # Sign a CSR. Body should at least include the 'csr' attribute
        # containing a PEM encoded CSR. May also include a list of alt_names,
        # ip_sans, and a ttl (e.g. 780h)

        pass

        req = pecan.request.json
        if not 'csr' in req:
            pecan.response.status = 400
            pecan.response.json = {
                'error': 'A POST to /v1/sign/cert must include a csr.'
            }
        else:
            csr = x509.load_pem_x509_csr(str(req['csr']).encode('utf-8'), default_backend())
            LOG.info('Received CSR \'%s\', subject = %s', req['csr'], csr.subject)
            signing_role = CONF['signing_role']
            csr = req['csr']
            common_name = req.get('common_name', None)
            ip_sans = req.get('ip_sans', [])
            alt_names = req.get('alt_names', [])
            # Set the TTL to be a year. We may want to bring this to a lower
            # value when we have a robust host side certificate handling in
            # place.
            ttl = req.get('ttl', '8760h')
            try:
                resp = self._vault.sign_csr(signing_role, csr,
                                            common_name, ip_sans, alt_names, ttl)
                pecan.response.json = resp.json()['data']
                pecan.response.status = 200
                LOG.info('status: 200')
            except requests.HTTPError as e:
                pecan.response.status = e.response.status_code
                pecan.response.json = e.response.json()
                LOG.info('status: %s', e.response.status_code)
                LOG.info('response json: %s', e.response.json())

        return pecan.response
"""
