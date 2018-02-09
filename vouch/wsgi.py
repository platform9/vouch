from pecan.deploy import deploy

# paste factory:
def app_factory(global_config, **local_conf):
    return deploy(global_config['config'])
