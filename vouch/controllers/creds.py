# pylint: disable=too-few-public-methods

import logging
import pecan
import re

from pecan import expose
from pecan.rest import RestController

from vouch.conf import CONF
from firkinize.configstore.consul import Consul
import requests

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
        self._consul = Consul(
            CONF['consul_url'],
            CONF['consul_token'],
        )
        self._prefix = 'customers/%s' % (CONF['customer_id'])

    @expose('json')
    def get(self, user):
        """
        GET /v1/creds/<user>
        Get the keystone credentials for a user
        :param user: The user to get the credentials for 
        :returns: 200 with the credentials
        """
        LOG.info('Fetching credentials for user')
        try:
            creds =  self._consul.kv_get(self._prefix+ '/keystone/users/%s/password' % user)
            pecan.response.status = 200
            pecan.response.json = creds
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                LOG.warning('Credentials not found for user: %s', user)
                return _json_error_response(pecan.response, 404, f'Credentials not found for user: {user}')
            else:
                LOG.error('HTTP error while fetching credentials: %s', e)
                return _json_error_response(pecan.response, 500, str(e)) 
        except Exception as e:
            LOG.error('Could not fetch credential from consul', e)
            return _json_error_response(pecan.response, 500, e)
        return pecan.response
