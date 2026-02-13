# pylint: disable=too-few-public-methods

import base64
import logging
import pecan

from pecan import expose
from pecan.rest import RestController

from kubernetes import client as kclient
from kubernetes import config as kconfig

from vouch_conf import CONF

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

class ListCredsController(RestController):
    def __init__(self):
        pass

    @expose('json')
    def get(self, user):
        """
        GET /v1/creds/<user>
        Get the keystone credentials for a user
        :param user: The user to get the credentials for 
        :returns: 200 with the credentials
        """
        LOG.info('Fetching credentials for user')

        kconfig.load_kube_config()
        v1 = kclient.CoreV1Api()

        try:
            secret = v1.read_namespaced_secret('keystone-creds-' + user, CONF['namespace'])
        except kclient.ApiException as e:
            # TODO: differentiate 404 from 500s
            LOG.error('Error while fetching credentials: %s', e)
            return _json_error_response(pecan.response, 500, str(e))

        encoded_password = secret.data['password']
        decoded_password = base64.b64decode(encoded_password).decode('utf-8')

        pecan.response.status = 200
        pecan.response.json = decoded_password

        return pecan.response
