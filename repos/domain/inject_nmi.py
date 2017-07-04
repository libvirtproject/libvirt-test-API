#!/usr/bin/env python

from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('guestname',)
optional_params = {}

NMI_INFO = "NMI received for unknown reason"


def inject_nmi(params):
    guestname = params['guestname']
    logger = params['logger']

    try:
        conn = sharedmod.libvirtobj['conn']
        domobj = conn.lookupByName(guestname)
        logger.info('inject NMI to domain.')
        domobj.injectNMI()
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        logger.error("inject NMI failed.")
        return 1

    mac = utils.get_dom_mac_addr(guestname)
    ip = utils.mac_to_ip(mac, 120)
    cmd = "grep '%s' /var/log/messages" % NMI_INFO
    logger.debug("cmd: %s" % cmd)
    ret, out = utils.remote_exec_pexpect(ip, "root", "redhat", cmd)
    if ret:
        logger.error("FAIL: inject NMI to guest failed.")
        logger.error("out : %s" % out)
        return 1

    logger.info("PASS: inject NMI to guest successful.")
    return 0
