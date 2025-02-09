#!/bin/env python

import logging
import os
import random
import requests
import string
import sys

from argparse import ArgumentParser
from firkinize.configstore.consul import Consul
from requests import HTTPError
from vaultlib.ca import VaultCA

logging.basicConfig(level=logging.DEBUG)

LOG = logging.getLogger(__name__)

"""
note from tdell:

Originally there lived a single "vouch" section at the customer level. It was written at a time
when we supported only single regions, and when multi-region support was finally added, it would be
clobbered by subsequent region deployments. This meant hosts could only be onboarded to the
region most recently deployed.

Now there are "service/vouch" sections at the region level. Though we have a legacy vouch
section at the customer level, please mostly ignore it.

The ca_signing_role was originally hosts-{customer_name}. But in it we find a policy for a single
region, so we had a choice to either add additional regions to this policy, or create policies
for each region. The latter decision was taken.

Now each region has its own ca_signing_role as hosts-{region_name}.

Some old deployments are extant. There is now a fabricate_missing_data() function that creates
a region-level vouch configuration during upgrade. In doing so it might create new vault tokens.

I did not enjoy untangling this.
"""

"""
init-region utility for setting up the vouch environment. Expects the following
as a starting point:

customers/<customer_uuid>/keystone
|-- users
|
customers/<customer_uuid>/vouch
|-- ca_name
|-- ca_common_name
|-- vault
|   |-- server_key (usually vault_servers/<vault_server_id>)
|
vault_servers/<vault_server_id>
|-- url
|-- admin_token

In init-region, we create a keystone user, and a vault role and limited access
token for host certificate signing. After we init, we should see:

customers/<customer_uuid>/keystone
|-- users
|   |-- vouch
|       |-- email
|       |-- password
|       |-- project
|       |-- role
|
customers/<customer_uuid>/vouch
|-- ca_name
|-- ca_common_name
|-- ca_signing_role
|-- keystone_user
|   |-- email
|   |-- password
|   |-- project
|   |-- role
|-- vault
|   |-- server_key (usually vault_servers/<vault_server_id>)
|   |-- url
|   |-- host_signing_token
|
vault_servers/<vault_server_id>
|-- url
|-- admin_token

"""


def parse_args():
    parser = ArgumentParser(description='Initialize vouch signing service')
    parser.add_argument('--config-url', default='http://localhost:8500',
                        help='Address of the config node, default http://localhost:8500')
    parser.add_argument('--customer-id',
                        help='The keystone customer id', required=True)
    parser.add_argument('--region-id',
                        help='The region id for which to bootstrap the keystone endpoint',
                        required=True)
    parser.add_argument('--config-token',
                        help='config access token, also looks for '
                             'env[\'CONSUL_HTTP_TOKEN\']')
    return parser.parse_args()


def random_string(length=16):
    """
    generate a string made of random numbers and letters that always starts
    with a letter.
    """
    secret_chars = string.ascii_letters + string.digits
    return ''.join([random.SystemRandom().choice(string.ascii_letters)] +
                   [random.SystemRandom().choice(secret_chars)
                    for _ in range(length - 1)])


def add_keystone_user(consul, customer_uuid):
    """
    Add configuration to both the vouch and keystone spaces. Will not
    overwrite existing user parameters. All in a single consul transaction.
    """
    # FIXME: The user appears twice to match the pattern of other services that
    # need a keystone user. Since confd can't look outside its prefix, the user
    # needs to be both in the region and the global keystone area. consul-template
    # will help with this. Since vouch is actually in the global space, this isn't
    # a problem, but I'm going to follow this pattern now until I can come up with
    # a better solution for the general problem.
    keystone_prefix = 'keystone/users/vouch/'
    vouch_prefix = 'vouch/keystone_user/'
    with consul.prefix('customers/%s' % customer_uuid):
        try:
            password = consul.kv_get('%spassword' % keystone_prefix)
            LOG.info('Using existing keystone password...')
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                LOG.info('Generating new keystone password...')
                password = random_string()
            else:
                raise

        updates = {}
        for prefix in [keystone_prefix, vouch_prefix]:
            updates[prefix + 'email'] = 'vouch'
            updates[prefix + 'password'] = password
            updates[prefix + 'project'] = 'services'
            updates[prefix + 'role'] = 'admin'
        consul.kv_put_txn(updates)
        LOG.info('Added vouch user')


def fabricate_missing_data(consul, customer_uuid, region_uuid):

    LOG.info(f'fabricating regional vouch config for {region_uuid}')

    cert_version = consul.kv_get(f'customers/{customer_uuid}/regions/{region_uuid}/certs/current_version')

    # Obtain the shared_ca_name, which is quite possibly clobbered. We only need the very first component
    # of this, the secrets engine, which might look like "pki" or "pki_prod" or "pki_pmkft", etc.

    # looks like "pki/versioned/9d524532-61f0-41ac-a85a-64a3f5ac0656/v0"

    shared_ca_name = consul.kv_get(f'customers/{customer_uuid}/vouch/ca_name')
    secrets_engine = shared_ca_name.split("/")[0]

    ca_name = f'{secrets_engine}/versioned/{region_uuid}/{cert_version}'

    # Our ca_common_name is always the DU shortname

    du_fqdn = consul.kv_get(f'customers/{customer_uuid}/regions/{region_uuid}/fqdn')
    ca_common_name = du_fqdn.split(".")[0]

    # Our ca_signing_role is per-region, but used to be per-customer

    ca_signing_role = f'hosts-{region_uuid}'

    # The server key is strange, since this seems to be an unneeded abstraction. We have
    # always called it 'dev' for some reason, so this is hardcoded in deccaxon and vouch now.

    server_key = f'customers/{customer_uuid}/vault_servers/dev'

    # Global across all regions

    vault_server = consul.kv_get(f'{server_key}/url')

    # The admin token has policies: [default kplane]
    # This is independent of region.

    admin_token = consul.kv_get(f'customers/{customer_uuid}/vault_servers/dev/admin_token')

    # Construct a tree to place under the region services "vouch" section

    vault_tree = {
        'url': vault_server,
        'server_key': server_key,
    }

    vault_servers_tree = {
        'dev': {
            'admin_token': admin_token,
            'url': vault_server,
        }
    }

    # these were in vouch_tree, but they are created at the end of this function
    # 'ca_signing_role': ca_signing_role,
    # 'host_signing_token': host_signing_token,

    vouch_tree = {
        'ca_common_name': ca_common_name,
        'ca_name': ca_name,
        'vault': vault_tree,
        'vault_servers': vault_servers_tree,
    }

    full_tree = { 'customers': { customer_uuid: { 'regions': { region_uuid: { 'services': { 'vouch': vouch_tree }}}}}}
    consul.kv_put_dict(full_tree)

    # The earlier, legacy host_signing_token had policies: [default hosts-{customer_uuid}]
    # But this has region-specific rules in it so it must be at the region level.
    # Instead, generate a new token and policy:

    vault = get_vault_admin_client(consul, customer_uuid)
    rolename = create_host_signing_role(vault, consul, customer_uuid, region_uuid)
    create_host_signing_token(vault, consul, customer_uuid, region_uuid, rolename)

    return ca_name


def get_vault_admin_client(consul, customer_uuid):
    region_uuid = os.environ['REGION_ID'] # to minimize signature changes

    try:
        ca_name = consul.kv_get(f'customers/{customer_uuid}/regions/{region_uuid}/services/vouch/ca_name')
    except requests.HTTPError as e:
        if e.response.status_code != 404:
            raise
        ca_name = fabricate_missing_data(consul, customer_uuid, region_uuid)

    ca_common_name = consul.kv_get(f'customers/{customer_uuid}/regions/{region_uuid}/services/vouch/ca_common_name')

    vault_server_key = consul.kv_get(f'customers/{customer_uuid}/regions/{region_uuid}/services/vouch/vault/server_key')
    with consul.prefix(vault_server_key):
        url = consul.kv_get('url')
        token = consul.kv_get('admin_token')

    return VaultCA(url, token, ca_name, ca_common_name)


def create_host_signing_role(vault, consul, customer_id, region_id) -> str:
    rolename = 'hosts-%s' % region_id
    customer_key: str = f'customers/{customer_id}/regions/{region_id}/services/vouch/ca_signing_role'
    try:
        val = consul.kv_get(customer_key)
        LOG.debug('kv_get for %s returned: %s', customer_key, val)
        if val == rolename:
            return rolename
    except HTTPError as err:
        if err.response.status_code != 404:
            LOG.error('cannot do kv_get on %s', customer_key, exc_info=err)
            raise err
    # either a) the signing role hasn't been created, or b) it has a customer-level one
    # older signing roles were hosts-{customer_id} not hosts-{region_id}
    vault.create_signing_role(rolename)
    consul.kv_put(customer_key, rolename)
    return rolename


def create_host_signing_token(vault, consul, customer_id, region_uuid, rolename, token_rolename='vouch-hosts'):
    policy_name = 'hosts-%s' % region_uuid
    customer_vault_url: str = f'customers/{customer_id}/regions/{region_uuid}/services/vouch/vault/url'
    customer_vault_hsk: str = f'customers/{customer_id}/regions/{region_uuid}/services/vouch/vault/host_signing_token'
    try:
        url = consul.kv_get(customer_vault_url)
        LOG.debug('consul kv_get on %s returned: %s', customer_vault_url, url)
        host_signing_token = consul.kv_get(customer_vault_hsk)
        LOG.debug('consul kv_get on %s returned: %s', customer_vault_hsk, host_signing_token)
    except HTTPError as err:
        if err.response.status_code != 404:
            LOG.error('cannot perform consul operation', exc_info=err)
            raise err
        vault.create_vouch_token_policy(rolename, policy_name)
        token_info = vault.create_token(policy_name, token_role=token_rolename)
        consul.kv_put(customer_vault_url, vault.addr)
        consul.kv_put(customer_vault_hsk, token_info.json()['auth']['client_token'])


def parse():
    args = parse_args()
    config_url = args.config_url or os.environ.get('CONSUL_HTTP_ADDR', None)
    token = args.config_token or os.environ.get('CONSUL_HTTP_TOKEN', None)
    consul = Consul(config_url, token=token)
    return args, consul

def new_token(consul, customer_id):
    # obtain the region_id from the environment. We do not want to change the
    # signature of this function since it is called from outside.
    region_id = os.environ['REGION_ID']

    vault = get_vault_admin_client(consul, customer_id)
    rolename = create_host_signing_role(vault, consul, customer_id, region_id)
    create_host_signing_token(vault, consul, customer_id, rolename)
