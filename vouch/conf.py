
# pylint: disable=global-statement
import os
import yaml

CONF = None

def set_config(config_file):
    global CONF
    if CONF:
        raise RuntimeError('You can only call set_config once!')
    with open(config_file) as f:
        CONF = yaml.load(f)

    # paste.ini and config.py can be absolute paths in the config.
    # If not, check relative to original config
    for key, default in [('paste_ini', 'paste.ini'),
                         ('pecan_conf', 'config.py')]:
        path = CONF.pop(key, default)
        if os.path.isabs(path):
            CONF[key] = path
        else:
            CONF[key] = os.path.abspath(os.path.join(
                os.path.dirname(config_file), path))
        if not os.path.isfile(CONF[key]):
            raise RuntimeError('Could not find config file %s at %s'
                               % (key, CONF[key]))
    try:
        customer_id = os.environ['CUSTOMER_ID']
        region_id = os.environ['REGION_ID']
        consul_url = os.environ['CONFIG_URL']
        consul_token = os.environ['CONSUL_HTTP_TOKEN']
        CONF['customer_id']=customer_id
        CONF['region_id']=region_id
        CONF['consul_url']=consul_url
        CONF['consul_token']=consul_token
    except KeyError as e:
        raise RuntimeError('Failed to set consul config, missing environment:', e)
