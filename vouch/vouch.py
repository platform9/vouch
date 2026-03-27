#!/usr/bin/env python3

import os
import logging

from sanic import Sanic, response
from sanic.log import logger

from ca import get_cas
from sign import get_current_ca, generate_new_ca_root_cert, sign_cert
from creds import get_keystone_creds
from cert_utils import set_logger

LOG = logging.getLogger(__name__)

app1 = Sanic("vouch-keystone")
app2 = Sanic("vouch-noauth")

KEYSTONE_PORT = 8448
NOAUTH_PORT = 8558

def dump_headers(request):

    logger.info(f'[{request.app.name}] {request.path}')

    for key, value in request.headers.items():
        logger.info(f'HEADER({key}): {value}')

@app1.route("/", methods=["GET"])
@app2.route("/", methods=["GET"])
async def root(request):

    dump_headers(request)
    region_fqdn = os.environ["REGION_FQDN"]

    reply = { 'v1': f'https://{region_fqdn}/vouch/v1' }
    return response.json(reply)

@app1.route("/ping", methods=["GET"])
@app2.route("/ping", methods=["GET"])
async def ping(request):

    dump_headers(request)
    return response.text("pong\n")

@app1.route("/v1/cas", methods=["GET"])
@app2.route("/v1/cas", methods=["GET"])
async def v1_cas(request):

    dump_headers(request)
    return get_cas(request)

@app1.route("/v1/sign/ca", methods=["GET"])
@app2.route("/v1/sign/ca", methods=["GET"])
async def v1_get_current_ca(request):

    dump_headers(request)
    return get_current_ca(request)

@app1.route("/v1/sign/ca", methods=["POST"])
@app2.route("/v1/sign/ca", methods=["POST"])
async def v1_generate_new_ca_root_cert(request):

    dump_headers(request)
    return generate_new_ca_root_cert(request)

@app1.route("/v1/sign/cert", methods=["POST"])
@app2.route("/v1/sign/cert", methods=["POST"])
async def v1_sign_cert(request):

    dump_headers(request)
    return sign_cert(request)

@app1.route("/v1/creds/<user>", methods=["GET"])
@app2.route("/v1/creds/<user>", methods=["GET"])
async def v1_get_keystone_creds(request, user):

    dump_headers(request)
    return get_keystone_creds(request, user)


if __name__ == "__main__":

    LOG.info("This is Radio Vouch")

    app_name = os.environ["APP"]
    if app_name == "vouch-keystone":
        port = KEYSTONE_PORT
    elif app_name == "vouch-noauth":
        port = NOAUTH_PORT
    else:
        raise Exception(f'unknown APP: "{app_name}"')

    set_logger(logger.info)

    app1.prepare(host="0.0.0.0", port=KEYSTONE_PORT, debug=True)
    app2.prepare(host="0.0.0.0", port=NOAUTH_PORT, debug=True)

    Sanic.serve()
