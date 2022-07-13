# pylint: disable=too-few-public-methods

import logging
import pecan
import re

from pecan import expose
from pecan.rest import RestController

from vouch.conf import CONF
from firkinize.configstore.consul import Consul

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
        self._consul = Consul(
            CONF['consul_url'],
            CONF['consul_token'],
        )
        self._prefix = 'customers/%s/regions/%s' % (CONF['customer_id'], CONF['region_id'])

    @expose('json')
    def get(self):
        """
        GET /v1/cas
        Get the list of all active root CAs
        """
        LOG.info('Fetching list of current ca certificates')
        try:
            certs =  self._consul.kv_get_prefix(self._prefix+ '/certs')
            active_ca = []
            for k in certs:
                pattern = '^'+ self._prefix +'/certs/v\d+/ca/cert$'
                if re.search(pattern,k):
                    active_ca.append(certs[k])
            pecan.response.status = 200
            pecan.response.json = active_ca
        except Exception as e:
            LOG.error('Could not fetch CA certs from consul', e)
            return _json_error_response(pecan.response, 500, e)
            pecan.response.status = 500
        return pecan.response
