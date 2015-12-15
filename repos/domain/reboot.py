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


def reboot(params):
    """Reboot virtual machine
       Return 0 on SUCCESS or 1 on FAILURE
    """
    # Initiate and check parameters
    global logger
    logger = params['logger']
    params.pop('logger')
    domain_name = params['guestname']

    # Connect to local hypervisor connection URI
    hypervisor = utils.get_hypervisor()
    if hypervisor == "kvm":
        logger.info("kvm hypervisor doesn't support the funtion now")
        return 0

    conn = sharedmod.libvirtobj['conn']
    domobj = conn.lookupByName(domain_name)

    # Get domain ip
    logger.info("get the mac address of vm %s" % domain_name)
    mac = utils.get_dom_mac_addr(domain_name)
    logger.info("the mac address of vm %s is %s" % (domain_name, mac))
    logger.info("get ip by mac address")
    ip = utils.mac_to_ip(mac, 180)
    logger.info("the ip address of vm %s is %s" % (domain_name, ip))
    timeout = 600
    logger.info('reboot vm %s now' % domain_name)

    # Reboot domain
    try:
        domobj = reboot(0)
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        logger.error("fail to reboot domain")
        return 1

    logger.info("the vm %s is power off" % domain_name)

    # Check domain status by ping ip
    while timeout:
        time.sleep(10)
        timeout -= 10
        if utils.do_ping(ip, 0):
            logger.info(str(timeout) + "s left")
        else:
            logger.info("vm %s power off successfully" % domain_name)
            break
        if timeout == 0:
            logger.info("fail to power off %s" % domain_name)
            return 1

    timeout = 600
    logger.info("the vm %s is power on" % domain_name)

    while timeout:
        time.sleep(10)
        timeout -= 10
        if not utils.do_ping(ip, 0):
            logger.info(str(timeout) + "s left")
        else:
            logger.info("vm %s power on successfully")
            break

        if timeout == 0:
            logger.info("fail to power on vm %s" % domain_name)
            return 1

    return 0
