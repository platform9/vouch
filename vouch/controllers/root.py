from vouch.controllers.sign import SignController

class V1Controller(object):
    '''
    Version 1 of the controller
    '''
    sign = SignController()


class RootController(object):
    '''
    Root controller class for the image library REST API
    '''
    v1 = V1Controller()
