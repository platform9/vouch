# pylint: disable=too-few-public-methods

import base64
import logging

from sanic import Sanic, response

from kubernetes import client as kclient
from kubernetes import config as kconfig

from vouch_conf import CONF

LOG = logging.getLogger(__name__)


@app.route("/v1/creds", methods=["GET"])
def get_keystone_creds(response):
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
            raise SanicException("Error fetchingn credentials", status_code=500)

        encoded_password = secret.data['password']
        decoded_password = base64.b64decode(encoded_password).decode('utf-8')

        return response.json(decoded_password)
