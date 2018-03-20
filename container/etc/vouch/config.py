# Server Specific Configurations
server = {
    'port': '8558',
    'host': '0.0.0.0'
}

# Pecan Application Configurations
app = {
    'root': 'vouch.controllers.root.RootController',
    'modules': ['vouch'],
    'debug': False,

    # this 'guess' also strips off the extension from the resource path.
    'guess_content_type_from_ext': False
}

logging = {
    'loggers': {
        'vouch': {'level': 'DEBUG', 'handlers': ['console']},
        'keystonemiddleware': {'level': 'DEBUG', 'handlers': ['console']},
        '__force_dict__': True
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        }
    },
    'formatters': {
        'simple': {
            'format': ('%(asctime)s %(levelname)s [%(name)s]'
                       '[%(threadName)s] %(message)s')
        }
    }
}
