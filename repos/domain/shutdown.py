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
optional_params = {'flags': 'none'}


def parse_flags(logger, params):
    flags = params.get('flags', 'none')
    logger.info('shutdown with flags :%s' % flags)
    if flags == 'none':
        return None
    ret = 0
    for flag in flags.split('|'):
        if flag == 'default':
            ret = ret | libvirt.VIR_DOMAIN_SHUTDOWN_DEFAULT
        elif flag == 'acpi':
            ret = ret | libvirt.VIR_DOMAIN_SHUTDOWN_ACPI_POWER_BTN
        elif flag == 'agent':
            ret = ret | libvirt.VIR_DOMAIN_SHUTDOWN_GUEST_AGENT
        #Flags below are not supported by kvm
        elif flag == 'initctl':
            ret = ret | libvirt.VIR_DOMAIN_SHUTDOWN_INITCTL
        elif flag == 'signal':
            ret = ret | libvirt.VIR_DOMAIN_SHUTDOWN_SIGNAL
        elif flag == 'paravirt':
            ret = ret | libvirt.VIR_DOMAIN_SHUTDOWN_PARAVIRT
        else:
            logger.error("flag is illegal.")
            return -1
    return ret


def shutdown(params):
    """Shutdown domain

        Argument is a dictionary with two keys:
        {'logger': logger, 'guestname': guestname}

        logger -- an object of utils/log.py
        guestname -- same as the domain name
        flag -- flags pass to shutdown

        Return 0 on SUCCESS or 1 on FAILURE
    """
    domname = params['guestname']
    logger = params['logger']
    flag = parse_flags(logger, params)
    if flag == -1:
        return 1

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
        if flag is None:
            domobj.shutdown()
        else:
            domobj.shutdownFlags(flag)
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
