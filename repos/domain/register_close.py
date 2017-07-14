import libvirt
import threading

from utils.events import virEventLoopPureThread
from utils import utils

required_params = ()
optional_params = {}

callback = False


def connCloseCallback(conn, reason, opaque):
    global callback

    callback = True


def restart_libvirtd(conn, logger):
    cmd = "service libvirtd restart"
    ret, out = utils.exec_cmd(cmd, shell=True)
    logger.info("cmd: %s" % cmd)
    if ret:
        logger.error("restart libvirtd failed.")
        logger.error("out: %s" % out)
        return 1

    return 0


def register_close(params):
    logger = params['logger']

    eventLoop = virEventLoopPureThread(logger)
    eventLoop.regist(libvirt)
    eventLoop.start()

    conn = libvirt.openReadOnly("qemu:///system")
    conn.registerCloseCallback(connCloseCallback, None)

    t = threading.Thread(target=restart_libvirtd, args=(conn, logger))

    t.start()
    t.join()

    if callback:
        logger.info("PASS: registerCloseCallback successful.")
    else:
        logger.error("FAIL: registerCloseCallback failed.")
        return 1

    return 0
