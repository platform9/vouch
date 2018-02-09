import logging
import pecan

from pecan.core import abort
from pecan import expose, conf
import os.path

from pprint import pformat
from vouch.conf import CONF

LOG = logging.getLogger(__name__)

class SignController(object):
    def __init__(self):
        pass

    @expose(content_type=None) # any content type is ok - check type below
    def _default(self, *path_elems):
        LOG.info(pformat(vars(pecan.request)))
        LOG.info(pformat(CONF))
        pecan.response.content_type = 'application/text'
        pecan.response.charset = None # defaults to UTF-8
        pecan.response.status = 200
        return pecan.response
