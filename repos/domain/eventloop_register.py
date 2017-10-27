import libvirt

from utils.events import virEventLoopPureThread

required_params = ()
optional_params = {}


def eventloop_register(params):
    logger = params['logger']

    eventLoop = virEventLoopPureThread(logger)
    eventLoop.regist(libvirt)
    eventLoop.start()

    return 0
