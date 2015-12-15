#!/usr/bin/env python
# Create domain from xml

import os
import re
import sys
import time

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

NONE = 0
START_PAUSED = 1

required_params = ('guestname', 'diskpath',)
optional_params = {'memory': 1048576,
                   'vcpu': 1,
                   'imageformat': 'raw',
                   'hddriver': 'virtio',
                   'nicdriver': 'virtio',
                   'macaddr': '52:54:00:97:e4:28',
                   'uuid': '05867c1a-afeb-300e-e55e-2673391ae080',
                   'virt_type': 'kvm',
                   'flags': 'none',
                   'xml': 'xmls/kvm_guest_define.xml',
                   'guestmachine': 'pc',
                   }


def create(params):
    """create a domain from xml"""
    logger = params['logger']
    guestname = params['guestname']
    xmlstr = params['xml']

    flags = params.get('flags', 'none')
    if flags != "none" and flags != "start_paused":
        logger.error("flags value either \"none\" or \"start_paused\"")
        return 1

    conn = sharedmod.libvirtobj['conn']

    # Create domain from xml
    try:
        if flags == "none":
            domobj = conn.createXML(xmlstr, NONE)
        elif flags == "start_paused":
            domobj = conn.createXML(xmlstr, START_PAUSED)
        else:
            logger.error("flags error")
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        logger.error("fail to create domain %s" % guestname)
        return 1

    if flags == "start_paused":
        state = domobj.info()[0]
        if state == libvirt.VIR_DOMAIN_PAUSED:
            logger.info("guest start with state paused successfully")
            return 0
        else:
            logger.error("guest state error")
            return 1

    logger.info("get the mac address of vm %s" % guestname)
    mac = utils.get_dom_mac_addr(guestname)
    logger.info("the mac address of vm %s is %s" % (guestname, mac))

    timeout = 600

    while timeout:
        time.sleep(10)
        timeout -= 10

        ip = utils.mac_to_ip(mac, 180)

        if not ip:
            logger.info(str(timeout) + "s left")
        else:
            logger.info("vm %s power on successfully" % guestname)
            logger.info("the ip address of vm %s is %s" % (guestname, ip))
            break

        if timeout == 0:
            logger.info("fail to power on vm %s" % guestname)
            return 1

    return 0
