#!/usr/bin/env python
# Restore domain from a saved statefile

import libvirt
import functools

from libvirt import libvirtError
from utils import utils

required_params = ('guestname', 'filepath',)
optional_params = {}


def get_guest_ipaddr(*args):
    """Get guest ip address"""
    (guestname, logger) = args

    mac = utils.get_dom_mac_addr(guestname)
    logger.debug("guest mac address: %s" % mac)

    ipaddr = utils.mac_to_ip(mac, 60)
    logger.debug("guest ip address: %s" % ipaddr)

    if utils.do_ping(ipaddr, 20) == 1:
        logger.info("ping current guest successfull")
        return ipaddr
    else:
        logger.error("Error: can't ping current guest")
        return None


def check_guest_status(*args):
    """Check guest current status"""
    (domobj, logger) = args

    state = domobj.info()[0]
    logger.debug("current guest status: %s" % state)

    if state == libvirt.VIR_DOMAIN_SHUTOFF or state == libvirt.VIR_DOMAIN_SHUTDOWN:
        return False
    else:
        return True


def check_guest_restore(*args):
    """Check restore domain result, if restore domain is successful,
       guest status will not be paused and can be ping
    """
    (guestname, domobj, logger) = args

    if check_guest_status(domobj, logger):
        if get_guest_ipaddr(guestname, logger):
            return True
        else:
            return False
    else:
        return False


def restore_guest(conn, filepath, logger):
    try:
        conn.restore(filepath)
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return False
    return True


def restore(params):
    """ retore a domain """
    logger = params['logger']
    guestname = params['guestname']
    filepath = params['filepath']

    conn = libvirt.open()
    domobj = conn.lookupByName(guestname)

    if check_guest_status(domobj, logger):
        logger.error("Error: current guest status is not shutoff or shutdown,\
                      can not do restore operation")
        return 1

    ret = utils.wait_for(functools.partial(restore_guest, conn, filepath, logger), 60, step=5)
    if not ret:
        logger.error("Error: fail to restore %s domain" % guestname)
        return 1
    if check_guest_restore(guestname, domobj, logger):
        logger.info("restore %s domain successful" % guestname)
    else:
        logger.error("Error: fail to check restore domain")
        return 1

    return 0
