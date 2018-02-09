import yaml

CONF = None

def set_config(filename):
    global CONF
    if CONF:
        raise RuntimeError('You can only call set_config once!')
    with open(filename) as f:
        CONF = yaml.load(f)
