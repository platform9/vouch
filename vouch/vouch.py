#!/usr/bin/env python3

import os
import logging
from sanic import Sanic, response
from vouch_conf import CONF, dump_headers
from ca import get_cas

LOG = logging.getLogger(__name__)

app = Sanic("Vouch")

@app.route("/ping", methods=["GET"])
async def ping(request):
    dump_headers(request)
    return response.text("pong")

@app.route("/v1/zing", methods=["GET"])
async def zing(request):
    dump_headers(request)
    return response.text("zong")

@app.route("/", methods=["GET"])
async def root(request):
    """
    Get links to the available versions
    """
    dump_headers(request)
    vouch_addr = CONF.get('vouch_addr', 'unknown')
    reply = { 'v1': '%s/v1' % vouch_addr }
    return response.json(reply)

@app.route("/v1/cas", methods=["GET"])
async def v1_cas(request):

    dump_headers(request)
    return get_cas(request)


if __name__ == "__main__":

    LOG.info("This is Radio Vouch")

    app_name = os.environ["APP"]
    if app_name == "vouch-keystone":
        port = 8448
    elif app_name == "vouch-noauth":
        port = 8558
    else:
        raise Exception("unknown APP: %s" % app_name)

    app.run(host="0.0.0.0", port=port, debug=True)
