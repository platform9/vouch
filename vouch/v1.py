from vouch.controllers.sign import SignController
from vouch.controllers.CA import ListCAController
from vouch.controllers.creds import ListCredsController

class V1Controller(object):
    sign = SignController()
    cas = ListCAController()
    creds = ListCredsController()
