# pylint: disable=too-few-public-methods

import base64
import logging
import os
import pecan
import re

from pecan import expose
from pecan.rest import RestController

from vouch_conf import CONF

from kubernetes import client as kclient
from kubernetes import config as kconfig

LOG = logging.getLogger(__name__)

def _json_error_response(response, code, exc):
    """
    json response from an exception object
    """
    response.status = code
    response.content_type = 'application/json'
    response.charset = 'utf-8'
    try:
        response.json = {'message': '%s: %s' % (exc.__class__.__name__, exc)}
    except Exception:
        response.json = {'message': 'Request Failed'}
    return response

class ListCAController(RestController):
    def __init__(self):
        pass

    @expose('json')
    def get(self):
        """
        GET /v1/cas
        Get the list of all active root CAs
        """

        LOG.info('Fetching list of current ca certificates')

        try:
            kconfig.load_kube_config()
        except kconfig.ConfigException:
            kconfig.load_incluster_config()

        v1 = kclient.CoreV1Api()
        namespace = os.environ["NAMESPACE"]

        active_ca = []
        try:
            secrets = v1.list_namespaced_secret(namespace=namespace)
        except:
            LOG.error('Could not fetch CA certs from kubernetes:', e)
            pecan.response.status = 500
            return _json_error_response(pecan.response, 500, e)

        if secrets and secrets.items:

            pattern = '^v\d+-ca-secret$'
            for secret in secrets.items:
                if re.search(pattern, secret.metadata.name):
                    data_b64 = secrets.data["ca.crt"]
                    data = base64.b64decode(data_b64)
                    active_ca.append(str(data))

        pecan.response.status = 200
        pecan.response.json = active_ca

        return pecan.response
