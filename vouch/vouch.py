#!/usr/bin/env python3

import os
import logging

from sanic import Sanic, response
from sanic.log import logger
from sanic.exceptions import SanicException, Forbidden

from auth import validate_keystone_token
from ca import get_cas
from sign import get_current_ca, generate_new_ca_root_cert, sign_cert
from creds import get_keystone_creds
from common_cert import set_logger

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

app1 = Sanic("vouch-keystone")
app2 = Sanic("vouch-noauth")

KEYSTONE_PORT = 8448
NOAUTH_PORT = 8558

async def validate(request):

    logger.info(f'[{request.app.name}] {request.path}')

    if request.app.name == 'vouch-noauth':
        return True, None

    candidate_token = request.headers.get('X-Auth-Token')
    validated, text = await validate_keystone_token(candidate_token)

    if text:
        logger.info(f'validated result: {text}')

    if not validated:
        return False, response.text("Unauthorized", status=401)
        # TODO: verify that this is an admin token

    return True, None

# root, this is used as a test of reachability

@app1.route("/", methods=["GET"])
@app2.route("/", methods=["GET"])
async def root(request):

    validated, rv = await validate(request)
    if not validated:
        return rv

    region_fqdn = os.environ["REGION_FQDN"]

    reply = { 'v1': f'https://{region_fqdn}/vouch/v1' }
    return response.json(reply)

# ping. No permissions required

@app1.route("/ping", methods=["GET"])
@app2.route("/ping", methods=["GET"])
async def ping(request):

    return response.text(f'{request.app.name} pong\n')

# request list of CAs

@app1.route("/v1/cas", methods=["GET"])
@app2.route("/v1/cas", methods=["GET"])
async def v1_cas(request):

    validated, rv = await validate(request)
    if not validated:
        return rv

    return get_cas(request)

# get current CA cert

@app1.route("/v1/sign/ca", methods=["GET"])
@app2.route("/v1/sign/ca", methods=["GET"])
async def v1_get_current_ca(request):

    validated, rv = await validate(request)
    if not validated:
        return rv

    return get_current_ca(request)

# generate a new CA root cert

@app1.route("/v1/sign/ca", methods=["POST"])
@app2.route("/v1/sign/ca", methods=["POST"])
async def v1_generate_new_ca_root_cert(request):

    validated, rv = await validate(request)
    if not validated:
        return rv

    return generate_new_ca_root_cert(request)

# sign a host cert

@app1.route("/v1/sign/cert", methods=["POST"])
@app2.route("/v1/sign/cert", methods=["POST"])
async def v1_sign_cert(request):

    validated, rv = await validate(request)
    if not validated:
        return rv

    return sign_cert(request)

# obtain service user credential

@app1.route("/v1/creds/<user>", methods=["GET"])
@app2.route("/v1/creds/<user>", methods=["GET"])
async def v1_get_keystone_creds(request, user):

    validated, rv = await validate(request)
    if not validated:
        return rv

    return get_keystone_creds(request, user)


if __name__ == "__main__":

    LOG.info("This is Radio Vouch")

    set_logger(logger.info)

    app1.prepare(host="0.0.0.0", port=KEYSTONE_PORT)
    app2.prepare(host="0.0.0.0", port=NOAUTH_PORT)

    Sanic.serve()

    LOG.info("O, untimely death!")
