#!/bin/env python

import logging
import os
import random
import requests
import string
import sys

from argparse import ArgumentParser
from firkinize.configstore.consul import Consul
from vaultlib.ca import VaultCA

logging.basicConfig(level=logging.DEBUG)

LOG = logging.getLogger(__name__)

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


def get_vault_admin_client(consul, customer_uuid):
    ca_name = consul.kv_get('customers/%s/vouch/ca_name' % customer_uuid)
    ca_common_name = consul.kv_get('customers/%s/vouch/ca_common_name' % customer_uuid)

    vault_server_key = consul.kv_get('customers/%s/vouch/vault/server_key'
                                     % customer_uuid)
    with consul.prefix(vault_server_key):
        url = consul.kv_get('url')
        token = consul.kv_get('admin_token')

    return VaultCA(url, token, ca_name, ca_common_name)


def create_host_signing_role(vault, consul, customer_id):
    rolename = 'hosts-%s' % customer_id
    vault.create_signing_role(rolename)
    consul.kv_put('customers/%s/vouch/ca_signing_role' % customer_id,
                  rolename)
    return rolename


def create_host_signing_token(vault, consul, customer_id, rolename, token_rolename='vouch-hosts'):
    policy_name = 'hosts-%s' % customer_id
    vault.create_vouch_token_policy(rolename, policy_name)
    token_info = vault.create_token(policy_name, token_role=token_rolename)
    consul.kv_put('customers/%s/vouch/vault/url' % customer_id, vault.addr)
    consul.kv_put('customers/%s/vouch/vault/host_signing_token' % customer_id,
                  token_info.json()['auth']['client_token'])


def parse():
    args = parse_args()
    config_url = args.config_url or os.environ.get('CONSUL_HTTP_ADDR', None)
    token = args.config_token or os.environ.get('CONSUL_HTTP_TOKEN', None)
    consul = Consul(config_url, token=token)
    return args, consul

def new_token(consul, customer_id):
    vault = get_vault_admin_client(consul, customer_id)
    rolename = create_host_signing_role(vault, consul, customer_id)
    create_host_signing_token(vault, consul, customer_id, rolename)
