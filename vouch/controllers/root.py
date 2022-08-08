from vouch.controllers.v1 import V1Controller
from vouch.controllers.metrics_controller import MetricsController
from pecan import expose
from pecan.rest import RestController

from vouch.conf import CONF

class RootController(RestController):
    v1 = V1Controller()
    metrics = MetricsController()

    @expose('json')
    def get(self):
        """
        Get links to the available versions
        """
        vouch_addr = CONF.get('vouch_addr', 'unknown')
        return {
            'v1': '%s/v1' % vouch_addr
        }
