import time
import libvirt
import threading

from utils.events import eventLoopPure
from utils.utils import exec_cmd, version_compare

required_params = ()
optional_params = {}

callback = False


def connCloseCallback(conn, reason, opaque):
    global callback

    callback = True


def restart_libvirtd(conn, logger):
    cmd = "service libvirtd restart"
    ret, out = exec_cmd(cmd, shell=True)
    logger.info("cmd: %s" % cmd)
    if ret:
        logger.error("restart libvirtd failed.")
        logger.error("out: %s" % out)
        return 1

    return 0


def register_close(params):
    logger = params['logger']

    if not version_compare("libvirt-python", 3, 8, 0, logger):
        eventLoopPure(logger)

    conn = libvirt.openReadOnly("qemu:///system")
    conn.registerCloseCallback(connCloseCallback, None)
    time.sleep(3)
    t = threading.Thread(target=restart_libvirtd, args=(conn, logger))

    t.start()
    t.join()

    if callback:
        logger.info("PASS: registerCloseCallback successful.")
    else:
        logger.error("FAIL: registerCloseCallback failed.")
        return 1

    return 0
