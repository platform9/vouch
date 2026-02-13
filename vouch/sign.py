# pylint: disable=too-few-public-methods

import base64
import json
import logging
import pecan
import requests

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from pecan import expose
from pecan.rest import RestController

from kubernetes import client as kclient
from kubernetes import config as kconfig

from vouch_conf import CONF
from cert_utils import get_latest_ca_cert


LOG = logging.getLogger(__name__)

# return the root CA
def get_ca_data():

    latest_ca, _, version = get_latest_ca_cert()

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

def sign_csr():

    pass

class CAController(RestController):
    def __init__(self):
        pass

    @expose('json')
    def get(self):
        """
        GET /v1/sign/ca
        Get the CA cert of the currently configured CA
        """

        LOG.info('Fetching current ca certificate')
        try:
            reply = get_ca_data()
            pecan.response.status = 200
            pecan.response.json = json.dumps(reply)
            LOG.info('status: 200')
        except requests.HTTPError as e:
            pecan.response.status = e.response.status_code
            pecan.response.json = e.response.json()
            LOG.info('status: %s', e.response.status_code)
            LOG.info('response json: %s', e.response.json())
        return pecan.response

    @expose('json')
    def post(self):
        """
        POST /v1/sign/ca
        Generate a new CA root certificate. Returns the old one and the
        new one.
        """
        resp_json = {}

        LOG.info('Refreshing ca certificate')
        try:
            old_cert_data = get_ca_data()
            resp_json['previous'] = json.dumps(old_cert_data)
            new_cert_data = refresh_ca_data()
            resp_json['new'] = json.dumps(new_cert_data)
            pecan.response.status = 200
            pecan.response.json = resp_json
            LOG.info('status: 200')
        except requests.HTTPError as e:
            pecan.response.status = e.response.status_code
            pecan.response.json = e.response.json()
            LOG.info('status: %s', e.response.status_code)
            LOG.info('response json: %s', e.response.json())
        return pecan.response


class CertController(RestController):
    def __init__(self):
        pass

    @expose('json')
    def post(self):
        """
        POST /v1/sign/cert
        Sign a CSR. Body should at least include the 'csr' attribute
        containing a PEM encoded CSR. May also include a list of alt_names,
        ip_sans, and a ttl (e.g. 780h)
        """

        pass

        """
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


class SignController(object):
    ca = CAController()
    cert = CertController()
