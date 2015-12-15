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
optional_params = {'flags': ''}

NONE = 0
START_PAUSED = 1


def start(params):
    """Start domain

        Argument is a dictionary with two keys:
        {'logger': logger, 'guestname': guestname}

        logger -- an object of utils/log.py
        mandatory arguments : guestname -- same as the domain name
        optional arguments : flags -- domain create flags <none|start_paused|noping>

        Return 0 on SUCCESS or 1 on FAILURE
    """
    domname = params['guestname']
    logger = params['logger']
    flags = params.get('flags', '')

    if "none" in flags and "start_paused" in flags:
        logger.error(
            "Flags error: Can't specify none and start_paused simultaneously")
        return 1

    conn = sharedmod.libvirtobj['conn']
    domobj = conn.lookupByName(domname)

    timeout = 600
    logger.info('start domain')

    try:
        if "none" in flags:
            domobj.createWithFlags(NONE)
        elif "start_paused" in flags:
            domobj.createWithFlags(START_PAUSED)
        else:
            # this covers flags = None as well as flags = 'noping'
            domobj.create()
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        logger.error("start failed")
        return 1

    if "start_paused" in flags:
        state = domobj.info()[0]
        if state == libvirt.VIR_DOMAIN_PAUSED:
            logger.info("guest start with state paused successfully")
            return 0
        else:
            logger.error("guest state error")
            return 1

    while timeout:
        state = domobj.info()[0]
        expect_states = [
            libvirt.VIR_DOMAIN_RUNNING,
            libvirt.VIR_DOMAIN_NOSTATE,
            libvirt.VIR_DOMAIN_BLOCKED]

        if state in expect_states:
            break

        time.sleep(10)
        timeout -= 10
        logger.info(str(timeout) + "s left")

    if timeout <= 0:
        logger.error('The domain state is not as expected, state: ' + state)
        return 1

    logger.info("Guest started")

    # Get domain ip and ping ip to check domain's status
    if "noping" not in flags:
        mac = utils.get_dom_mac_addr(domname)
        logger.info("get ip by mac address")
        ip = utils.mac_to_ip(mac, 180)

        logger.info('ping guest')
        if not utils.do_ping(ip, 300):
            logger.error('Failed on ping guest, IP: ' + str(ip))
            return 1

    logger.info("PASS")
    return 0
