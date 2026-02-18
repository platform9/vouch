#!/usr/bin/env python3

import os
from sanic import Sanic, response

app = Sanic("Vouch")

@app.route("/ping", methods=["GET"])
async def ping(request):
    return response.text("pong")

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
