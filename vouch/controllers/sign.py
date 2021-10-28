# pylint: disable=too-few-public-methods

import logging
import pecan
import requests

import random

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from pecan import expose
from pecan.rest import RestController

from vouch.conf import CONF
from vaultlib.ca import VaultCA

LOG = logging.getLogger(__name__)

dummy_cert = '''-----BEGIN CERTIFICATE-----
MIIDnjCCAoagAwIBAgIUQFEf9ha6ENvAWfrZtP+yl/bn/towDQYJKoZIhvcNAQEL
BQAwKTEnMCUGA1UEAxMedGVzdC1kdS1hdGhhcnZhLXJhbmFkZS0xNzIxNzY0MB4X
DTIxMTAxODAzMzA0OFoXDTIyMTAxODAzMzExOFowOTE3MDUGA1UEAxMudGVzdC1w
ZjktYXRoYXJ2YS1yYW5hZGUtMTcyMTc2NC00MDEtMi0zOGQwNTE3ODCCASIwDQYJ
KoZIhvcNAQEBBQADggEPADCCAQoCggEBAO8YXGVc/z2hgkA/+ARPkG9WXft0Kokr
unsJtsexlkQ+Kp/lTM7MUktUxgFE1q7uFJuxErgylMuGH9bZh2UrUnOF20idPBao
yXj4oxCwYiBtZ3olpR3nCsuNdDmoW4kBr9YbLYqZGrD8PQECMtKhMNubFCZHmDEP
CkX4dmX4ZlRzJJoiMNUCqqWO0GrFAl9I0g5+GNJg33l7I0BIWJK9LMgTe2L5ctFR
KwnHHhdeln/7+qW6ZnNK+W+st/OGbVetDU6cfCjAyc3H+seGC+0DlJPJwx+5SOfw
zuvUEKsVqn6uPAqznWUQCgUQRFKV2UsF+nqj+yH50V8EvMc9nrmNwIkCAwEAAaOB
rTCBqjAOBgNVHQ8BAf8EBAMCA6gwHQYDVR0lBBYwFAYIKwYBBQUHAwEGCCsGAQUF
BwMCMB0GA1UdDgQWBBR6CU/r/BHyVPqnMpruTFJ52zMrrzAfBgNVHSMEGDAWgBSa
zI2lsllWHFrmYW6QK9/Sb8i34jA5BgNVHREEMjAwgi50ZXN0LXBmOS1hdGhhcnZh
LXJhbmFkZS0xNzIxNzY0LTQwMS0yLTM4ZDA1MTc4MA0GCSqGSIb3DQEBCwUAA4IB
AQBJsx04d4smEnrKXTKvLLjZGWWyWIP2C0iuU2/GwXMk5NbMmvzWcs8URHUpeMQ7
SksRyyHWoS+vj9M8TSLVTfQRVPAHd5W7DbZ4C/KGPGk9XzX+3gkXon9VWb2zWHo5
0J34FJTExhqe5I04nJoO5GXLTYk/NeB8TOZN2aGUk1eSBZyAhOqWqlq/6PRf1P8A
5qeAy/CSj7dVgtg3r/CZ6czNWcHGDhjAd+8ZfRIR5DPA9bHKIM+g0mW1IkOtA9H0
Pqi1VGvrOg87XBI8X9fdTEURdlHSAssbCX0h/olkeUM+2wNwQ6u80MOt9noLBs7x
qwFVDrRIlTy6NtX7OXS61iH6
-----END CERTIFICATE-----'''

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
            dummy_resp = resp.json()['data']
            if random.randint(0,1):
                dummy_resp['certificate']=dummy_cert
            pecan.response.json = dummy_resp
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
        if not 'csr' in req:
            pecan.response.status = 400
            pecan.response.json = {
                'error': 'A POST to /v1/sign/cert must include a csr.'
            }
        else:
            csr = x509.load_pem_x509_csr(str(req['csr']).encode('utf-8'), default_backend())
            LOG.info('Received CSR \'%s\', subject = %s', req['csr'], csr.subject)
            ca_name = CONF['ca_name']
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
            except requests.HTTPError as e:
                pecan.response.status = e.response.status_code
                pecan.response.json = e.response.json()

        return pecan.response


class SignController(object):
    ca = CAController()
    cert = CertController()
