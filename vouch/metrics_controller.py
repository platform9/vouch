
import base64
import logging
import os
import time
import requests
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from sanic import Sanic, response

from prometheus_client import generate_latest, Gauge

from kubernetes import client as kclient
from kubernetes import config as kconfig

from cert_utils import get_latest_ca_cert

# Exporter gauges
g_ca_cert_refresh_needed = Gauge('refresh_needed', 'Is CA cert refresh needed?')
g_ca_cert_expiry_time = Gauge('cert_expiry_time', 'Time in seconds till CA cert expires')

LOG = logging.getLogger(__name__)

"""
class  MetricsController(RestController):
    def __init__(self):
        self.last_update_time = time.time()
        cert, _, _ = get_latest_ca_cert()
        self.cert_expiration_time = cert.not_valid_after

    def get_cert_expiration_time(self):
        current_time = time.time()
        if ((current_time - self.last_update_time) > CONF['vault_query_interval']):
            cert, _ = get_latest_ca_cert()
            self.cert_expiration_time = cert.not_valid_after
            self.last_update_time = current_time
        return self.cert_expiration_time

    @expose(content_type='text/plain')
    def get(self):
        # GET /metrics
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
"""
