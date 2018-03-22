#!/usr/bin/env python

import time

from libvirt import libvirtError
from src import sharedmod
from utils import utils

required_params = ('guestname', 'username', 'password')
optional_params = {}


def get_num_row(domobj, logger, username, password, ip):
    #get the current row number of "last reboot"'result
    cmd = "last reboot | wc -l"
    ret, output = utils.remote_exec_pexpect(ip, username, password, cmd)
    if ret:
        logger.error("fail to remote exec cmd: ret: %s, output: %s"
                     % (ret, output))
        return None
    logger.debug("the cmd output is %s" % output)
    return int(output)


def reset(params):
    """Reset a domain immediately without any guest OS shutdown
       Return 0 on SUCCESS or 1 on FAILURE
       Note:reset function just a reset of hardware,it don't shutdown guest.
            Resetting a virtual machine does not apply any pending domain configuration
            changes. Changes to the domain's configuration only take effect after a
            complete shutdown and restart of the domain.
    """
    guestname = params['guestname']
    logger = params['logger']

    username = params['username']
    password = params['password']

    conn = sharedmod.libvirtobj['conn']
    domobj = conn.lookupByName(guestname)

    logger.info("get the mac address of vm %s" % guestname)
    mac = utils.get_dom_mac_addr(guestname)
    logger.info("the mac address of vm %s is %s" % (guestname, mac))
    logger.info("get ip by mac address")
    ip = utils.mac_to_ip(mac, 180)
    logger.info("the ip address of vm %s is %s" % (guestname, ip))

    old_times = get_num_row(domobj, logger, username, password, ip)
    if old_times is None:
        return 1

    #reset domain
    try:
        logger.info("reset vm %s now" % guestname)
        domobj.reset(0)
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("fail to reset domain")
        return 1

    time.sleep(40)
    new_times = get_num_row(domobj, logger, username, password, ip)
    if new_times is None:
        return 1
    if new_times != old_times + 1:
        logger.error("fail to reset guest")
        return 1

    logger.info("vm %s reset successfully" % guestname)
    logger.info("PASS")
    return 0
