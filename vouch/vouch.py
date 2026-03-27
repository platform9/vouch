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

# root, this is used as a test of reachability

@app1.route("/", methods=["GET"])
async def a1_root(request):

    dump_headers(request)
    region_fqdn = os.environ["REGION_FQDN"]

    reply = { 'v1': f'https://{region_fqdn}/vouch/v1' }
    return response.json(reply)

@app2.route("/", methods=["GET"])
async def a2_root(request):

    dump_headers(request)
    region_fqdn = os.environ["REGION_FQDN"]

    reply = { 'v1': f'https://{region_fqdn}/vouch/v1' }
    return response.json(reply)

# ping

@app1.route("/ping", methods=["GET"])
async def a1_ping(request):

    dump_headers(request)
    return response.text("app1 pong\n")

@app2.route("/ping", methods=["GET"])
async def a2_ping(request):

    dump_headers(request)
    return response.text("app2 pong\n")

# request list of CAs

@app1.route("/v1/cas", methods=["GET"])
async def a1_v1_cas(request):

    dump_headers(request)
    return get_cas(request)

@app2.route("/v1/cas", methods=["GET"])
async def a2_v1_cas(request):

    dump_headers(request)
    return get_cas(request)

# get current CA cert

@app1.route("/v1/sign/ca", methods=["GET"])
async def a1_v1_get_current_ca(request):

    dump_headers(request)
    return get_current_ca(request)

@app2.route("/v1/sign/ca", methods=["GET"])
async def a2_v1_get_current_ca(request):

    dump_headers(request)
    return get_current_ca(request)

# generate a new CA root cert

@app1.route("/v1/sign/ca", methods=["POST"])
async def a1_v1_generate_new_ca_root_cert(request):

    dump_headers(request)
    return generate_new_ca_root_cert(request)

@app2.route("/v1/sign/ca", methods=["POST"])
async def a2_v1_generate_new_ca_root_cert(request):

    dump_headers(request)
    return generate_new_ca_root_cert(request)

# sign a host cert

@app1.route("/v1/sign/cert", methods=["POST"])
async def a1_v1_sign_cert(request):

    dump_headers(request)
    return sign_cert(request)

@app2.route("/v1/sign/cert", methods=["POST"])
async def a2_v1_sign_cert(request):

    dump_headers(request)
    return sign_cert(request)

# obtain service user credential

@app1.route("/v1/creds/<user>", methods=["GET"])
async def a1_v1_get_keystone_creds(request, user):

    dump_headers(request)
    return get_keystone_creds(request, user)

@app2.route("/v1/creds/<user>", methods=["GET"])
async def a2_v1_get_keystone_creds(request, user):

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

    Sanic.serve(app1, app2)

    LOG.info("O, untimely death!")
