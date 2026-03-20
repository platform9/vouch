# pylint: disable=too-few-public-methods

import base64
import logging
import os
import re

from vouch_conf import CONF, dump_headers

from kubernetes import client as kclient
from kubernetes import config as kconfig

from sanic.exceptions import SanicException

LOG = logging.getLogger(__name__)


def get_cas(request):
        """
        Get the list of all active root CAs
        """

        dump_headers(request)

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
        except Exception as e:
            LOG.error('Could not fetch CA certs from kubernetes:', e)
            raise SanicException("Could not fetch CA certs from kubernetes", status_code=500)

        if secrets and secrets.items:

            pattern = '^v\d+-ca-secret$'
            for secret in secrets.items:
                if re.search(pattern, secret.metadata.name):
                    data_b64 = secret.data["ca.crt"]
                    data = base64.b64decode(data_b64)
                    active_ca.append(str(data))

        return response.json(active_ca)
