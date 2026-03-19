from vouch_conf import CONF
from sanic import Sanic, response

@app.route("/", methods=["GET"])
async def root(request):
        """
        Get links to the available versions
        """
        vouch_addr = CONF.get('vouch_addr', 'unknown')
        reply = { 'v1': '%s/v1' % vouch_addr }
        return response.json(reply)
