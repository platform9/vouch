# pylint: disable=too-few-public-methods

import logging
import pecan
import requests

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from pecan import expose
from pecan.rest import RestController

from vouch.conf import CONF
from vaultlib.ca import VaultCA

LOG = logging.getLogger(__name__)


class CAController(RestController):
    def __init__(self):
        self._vault = VaultCA(
            CONF['vault_addr'],
            CONF['vault_token'],
            CONF['ca_name'],
            CONF['ca_common_name'],
        )

    @expose('json')
    def get(self):
        """
        GET /v1/sign/ca
        Get the CA cert of the currently configured CA
        """
        ca_name = CONF['ca_name']
        LOG.info('Fetching current ca certificate for %s.', ca_name)
        try:
            resp = self._vault.get_ca()
            pecan.response.status = 200
            pecan.response.json = resp.json()['data']
        except requests.HTTPError as e:
            pecan.response.status = e.response.status_code
            pecan.response.json = e.response.json()
        return pecan.response

    @expose('json')
    def post(self):
        """
        POST /v1/sign/ca
        Generate a new CA root certificate. Returns the old one and the
        new one.
        """
        resp_json = {}
        ca_name = CONF['ca_name']
        ca_common_name = CONF['ca_common_name']

        LOG.info('Refreshing ca certificate for %s.', ca_name)
        try:
            resp_old = self._vault.get_ca()
            resp_json['previous'] = resp_old.json()['data']
            resp_new = self._vault.new_ca_root(ca_common_name)
            resp_json['new'] = resp_new.json()['data']
            pecan.response.status = 200
            pecan.response.json = resp_json
        except requests.HTTPError as e:
            pecan.response.status = e.response.status_code
            pecan.response.json = e.response.json()
        return pecan.response


class CertController(RestController):
    def __init__(self):
        self._vault = VaultCA(
            CONF['vault_addr'],
            CONF['vault_token'],
            CONF['ca_name'],
            CONF['ca_common_name'],
        )

    @expose('json')
    def post(self):
        """
        POST /v1/sign/cert
        Sign a CSR. Body should at least include the 'csr' attribute
        containing a PEM encoded CSR. May also include a list of alt_names,
        ip_sans, and a ttl (e.g. 780h)
        """
        req = pecan.request.json
        if not req.has_key('csr'):
            pecan.response.status = 400
            pecan.response.json = {
                'error': 'A POST to /v1/sign/cert must include a csr.'
            }
        else:
            csr = x509.load_pem_x509_csr(str(req['csr']), default_backend())
            LOG.info('Received CSR \'%s\', subject = %s', req['csr'], csr.subject)
            ca_name = CONF['ca_name']
            signing_role = CONF['signing_role']
            csr = req['csr']
            common_name = req.get('common_name', None)
            ip_sans = req.get('ip_sans', [])
            alt_names = req.get('alt_names', [])
            ttl = req.get('ttl', '730h')
            try:
                resp = self._vault.sign_csr(signing_role, csr,
                                            common_name, ip_sans, alt_names, ttl)
                pecan.response.json = resp.json()['data']
                pecan.response.status = 200
            except requests.HTTPError as e:
                pecan.response.status = e.response.status_code
                pecan.response.json = e.response.json()

        return pecan.response


class SignController(object):
    ca = CAController()
    cert = CertController()
