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


def suspend(params):
    """Suspend domain

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

    # Suspend domain
    logger.info('suspend domain')
    try:
        domobj.suspend()
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1
    time.sleep(1)
    state = domobj.info()[0]

    if state != libvirt.VIR_DOMAIN_PAUSED:
        logger.error('The domain state is not equal to "paused"')
        return 1

    mac = utils.get_dom_mac_addr(domname)

    time.sleep(3)
    logger.info("get ip by mac address")
    ip = utils.mac_to_ip(mac, 10)

    time.sleep(10)

    logger.info('ping guest')
    if utils.do_ping(ip, 20):
        logger.error('The guest is still active, IP: ' + str(ip))
        return 1

    logger.info('PASS')
    return 0
