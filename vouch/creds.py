# pylint: disable=too-few-public-methods

import base64
import logging
import os

from sanic import Sanic, response

from kubernetes import client as kclient
from kubernetes import config as kconfig

LOG = logging.getLogger(__name__)


def get_keystone_creds(request, user):
        """
        GET /v1/creds/<user>
        Get the keystone credentials for a user
        :param user: The user to get the credentials for 
        :returns: 200 with the credentials
        """
        LOG.info('Fetching credentials for user:', user)

        # all keystone passwords should be in the customer secret with this pattern
        kp_env_var = user.upper() + '_KEYSTONE_PASSWORD'

        # notes from tdell
        # This function seems like a TERRIBLE idea. If possible, the
        # credentials should be provided to the consumer as environment
        # variables. If this is not possible, at the very least this
        # function should whitelist appropriate usernames.
        # The only usage I could locate was by Castellan, and that doesn't
        # seem to be packaged presently.

        password = os.environ.get(kp_env_var, "")

        return response.json(password)
