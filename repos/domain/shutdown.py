#!/usr/bin/env python

import os
import sys
import re
import time

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('guestname',)
optional_params = {}


def shutdown(params):
    """Shutdown domain

        Argument is a dictionary with two keys:
        {'logger': logger, 'guestname': guestname}

        logger -- an object of utils/log.py
        guestname -- same as the domain name

        Return 0 on SUCCESS or 1 on FAILURE
    """
    domname = params['guestname']
    logger = params['logger']

    conn = sharedmod.libvirtobj['conn']
    domobj = conn.lookupByName(domname)

    timeout = 600
    logger.info('shutdown domain')
    mac = utils.get_dom_mac_addr(domname)
    logger.info("get ip by mac address")
    ip = utils.mac_to_ip(mac, 180)
    logger.info("the ip address of guest is %s" % ip)

    # Shutdown domain
    try:
        domobj.shutdown()
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        logger.error("shutdown failed")
        return 1

    # Check domain status by ping ip
    while timeout:
        time.sleep(10)
        timeout -= 10
        logger.info(str(timeout) + "s left")

        state = domobj.info()[0]
        if state == libvirt.VIR_DOMAIN_SHUTOFF:
            break

    if timeout <= 0:
        logger.error('The domain state is not equal to "shutoff"')
        return 1

    logger.info('ping guest')
    if utils.do_ping(ip, 300):
        logger.error('The guest is still active, IP: ' + str(ip))
        return 1
    else:
        logger.info("domain %s shutdown successfully" % domname)

    return 0
