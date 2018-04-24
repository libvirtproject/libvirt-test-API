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
optional_params = {'flags': 'noping',
                   'bridgename': 'virbr0',
                   'virt_type': 'kvm',
                   }


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
    virt_type = params.get('virt_type', 'kvm')
    flags = ""
    if 'flags' in params:
        flags = params['flags']

    if "lxc" in virt_type:
        conn = libvirt.open("lxc:///")
    else:
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

    if "lxc" in virt_type:
        flags = "noping"

    if "noping" not in flags:
        # Get domain ip
        mac = utils.get_dom_mac_addr(guestname)
        logger.info("get ip by mac address")
        ip = utils.mac_to_ip(mac, 180, br)
        logger.info("the ip address of guest is %s" % ip)

    # Destroy domain
    try:
        domobj.destroy()
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("failed to destroy domain")
        # Add for test
        err_msg = "Some processes refused to die"
        if "lxc" in virt_type and err_msg in e.get_error_message():
            try:
                time.sleep(10)
                domobj.destroy()
            except libvirtError as e:
                logger.error("Still destroy error: %s" % e.get_error_message())
                return 1
        # End for test
        else:
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
