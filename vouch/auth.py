# validate that a provided candidate token is valid

import asyncio
import logging
import os
import requests
import time

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
LOG = logging.getLogger(__name__)

_token = None
_timestamp = None
_validations = {}

cache_lock = asyncio.Lock()

def _get_vouch_keystone_token():

    global _token
    global _timestamp

    infra_fqdn = os.environ["INFRA_FQDN"]
    vouch_keystone_user = os.environ["VOUCH_KEYSTONE_USER"]
    vouch_keystone_password = os.environ["VOUCH_KEYSTONE_PASSWORD"]

    url = f'https://{infra_fqdn}/keystone/v3/auth/tokens?nocatalog'

    headers = { "Content-Type": "application/json" }

    payload = {
            "auth": {
                "identity": {
                    "methods": ["password"],
                    "password": {
                        "user": {
                            "name": vouch_keystone_user,
                            "domain": { "id": "default" },
                            "password": vouch_keystone_password,
                        }
                    }
                }
            }
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 201:
        LOG.info(f'_get_vouch_keystone_token() status_code {response.status_code}')

    if response.status_code < 200 or response.status_code > 299:
        # unlikely that this ever occurs, since in most cases an exception is already raised
        raise Exception('failed to obtain a vouch keystone token: status code is {response.status_code}')

    subject_token = response.headers.get('X-Subject-Token')
    if not subject_token:
        raise Exception("ain't got no subject token. this should never occur! ever!")

    _token = subject_token
    _timestamp = time.time()

def get_vouch_keystone_token():

    if not _timestamp or time.time() - _timestamp > 3600:
        success = False
        last_error = None
        for i in range(0, 5):
            try:
                _get_vouch_keystone_token()
                success = True
                break
            except Exception as e:
                last_error = e
                LOG.info(f"error obtaining vouch's keystone token: {e}")
            time.sleep(1 + i)
        if not success:
            raise(f"was never able to obtain a vouch keystone token, error {last_error}")

    return _token

async def check_cached_token(candidate_token):

    async with cache_lock:
        timestamp = _validations.get(candidate_token, 0)
        if not timestamp:
            return False
        if time.time() - timestamp > 3600:
            del _validations[candidate_token]
            return False
        return True

async def cache_candidate_token(candidate_token):

    async with cache_lock:
        _validations[candidate_token] = time.time()

async def validate_keystone_token(candidate_token):

    cached = await check_cached_token(candidate_token)
    if cached:
        LOG.info(f'candidate token was in cache, accepted')
        return True, None

    # this does not actually need a lock around it
    token = get_vouch_keystone_token()

    headers = {
        "X-Auth-Token": token,
        "X-Subject-Token": candidate_token,
    }

    infra_fqdn = os.environ["INFRA_FQDN"]
    url = f'https://{infra_fqdn}/keystone/v3/auth/tokens'

    success = False
    last_error = None
    for i in range(0, 5):
        try:
            response = requests.get(url, headers=headers)
            success = True
            break
        except Exception as e:
            last_error = e
            LOG.info(f'failed to validate token: {e}')
        time.sleep(1 + i)

    if not success:
        raise Exception(f"error validating caller's keystone token: {e}")

    if response.status_code != 200:
        # we expect a 200 from the token validation, display if it isn't what we thought
        LOG.info(f'response status {response.status_code}')

    if response.status_code >= 200 and response.status_code <= 299:
        # but allow any 2xx
        await cache_candidate_token(candidate_token)
        return True, response.text

    return False, None
