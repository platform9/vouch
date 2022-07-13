from vouch.controllers.sign import SignController
from vouch.controllers.CA import ListCAController

class V1Controller(object):
    sign = SignController()
    cas = ListCAController()
