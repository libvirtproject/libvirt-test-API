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
optional_params = {'flags': 'noping', 'bridgename': 'virbr0', }


def destroy(params):
    """destroy domain
       Argument is a dictionary with two keys:
       {'guestname': guestname}

       logger -- an object of utils/log.py
       guestname -- the domain name
       flags -- optional arguments:
                  noping: Don't do the ping test


       Return 0 on SUCCESS or 1 on FAILURE
    """
    # Initiate and check parameters
    global logger
    logger = params['logger']
    params.pop('logger')
    guestname = params['guestname']
    br = params.get('bridgename', 'virbr0')
    flags = ""
    if 'flags' in params:
        flags = params['flags']

    conn = sharedmod.libvirtobj['conn']

    # Get running domain by name
    guest_names = []
    ids = conn.listDomainsID()
    for id in ids:
        obj = conn.lookupByID(id)
        guest_names.append(obj.name())

    if guestname not in guest_names:
        logger.error("guest %s doesn't exist or isn't running." % guestname)
        return 1

    domobj = conn.lookupByName(guestname)

    timeout = 60
    logger.info('destroy domain')

    if "noping" not in flags:
        # Get domain ip
        mac = utils.get_dom_mac_addr(guestname)
        logger.info("get ip by mac address")
        ip = utils.mac_to_ip(mac, 180, br)
        logger.info("the ip address of guest is %s" % ip)

    # Destroy domain
    try:
        domobj.destroy()
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        logger.error("failed to destroy domain")
        return 1

    # Check domain status by ping ip
    if "noping" not in flags:
        while timeout:
            time.sleep(10)
            timeout -= 10
            logger.info(str(timeout) + "s left")

            logger.info('ping guest')

            if utils.do_ping(ip, 30):
                logger.error('The guest is still active, IP: ' + str(ip))
                return 1
            else:
                logger.info("domain %s was destroyed successfully" % guestname)
                break

        if timeout <= 0:
            logger.error("the domain couldn't be destroyed within 60 seconds.")
            return 1

    return 0
