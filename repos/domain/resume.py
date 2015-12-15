#!/usr/bin/env python

import os
import sys
import re

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('guestname',)
optional_params = {}


def resume(params):
    """Resume domain

        Argument is a dictionary with two keys:
        {'logger': logger, 'guestname': guestname}

        logger -- an object of utils/log.py
        guestname -- same as the domain name

        Return 0 on SUCCESS or 1 on FAILURE
    """
    domname = params['guestname']
    logger = params['logger']

    # Resume domain
    conn = sharedmod.libvirtobj['conn']
    domobj = conn.lookupByName(domname)
    logger.info('resume domain')
    try:
        domobj.resume()
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        logger.error("resume failed")
        return 1

    state = domobj.info()[0]
    expect_states = [
        libvirt.VIR_DOMAIN_RUNNING,
        libvirt.VIR_DOMAIN_NOSTATE,
        libvirt.VIR_DOMAIN_BLOCKED]

    if state not in expect_states:
        logger.error('The domain state is not equal to "paused"')
        return 1

    mac = utils.get_dom_mac_addr(domname)
    logger.info("get ip by mac address")
    ip = utils.mac_to_ip(mac, 120)

    logger.info('ping guest')
    if not utils.do_ping(ip, 300):
        logger.error('Failed on ping guest, IP: ' + str(ip))
        return 1

    logger.info("PASS")
    return 0
