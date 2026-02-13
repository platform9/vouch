from sign import SignController
from ca import ListCAController
from creds import ListCredsController

class V1Controller(object):
    sign = SignController()
    cas = ListCAController()
    creds = ListCredsController()
