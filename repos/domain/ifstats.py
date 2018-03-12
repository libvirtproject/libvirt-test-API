#!/usr/bin/evn python
# To get domain interface statistics

import os
import re
import sys
import time
import libxml2

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('guestname',)
optional_params = {}


def check_guest_status(domobj):
    """Check guest current status"""
    state = domobj.info()[0]
    if state == libvirt.VIR_DOMAIN_SHUTOFF or state == libvirt.VIR_DOMAIN_SHUTDOWN:
        # add check function
        return False
    else:
        return True


def check_interface_stats():
    """Check interface statistic result"""
    pass


def ifstats(params):
    """Domain interface statistic"""
    logger = params['logger']
    guestname = params['guestname']

    conn = sharedmod.libvirtobj['conn']
    domobj = conn.lookupByName(guestname)

    if check_guest_status(domobj):
        pass
    else:
        try:
            logger.info("%s is not running , power on it" % guestname)
            domobj.create()
        except libvirtError as e:
            logger.error("API error message: %s, error code is %s"
                         % (e.message, e.get_error_code()))
            logger.error("start failed")
            return 1

    mac = utils.get_dom_mac_addr(guestname)
    logger.info("get ip by mac address")
    ip = utils.mac_to_ip(mac, 180)

    logger.info('ping guest')
    if not utils.do_ping(ip, 300):
        logger.error('Failed on ping guest, IP: ' + str(ip))
        return 1

    xml = domobj.XMLDesc(0)
    doc = libxml2.parseDoc(xml)
    ctx = doc.xpathNewContext()
    devs = ctx.xpathEval("/domain/devices/interface/target/@dev")
    path = devs[0].content
    ifstats = domobj.interfaceStats(path)

    if ifstats:
        # check_interface_stats()
        logger.debug(ifstats)
        logger.info("%s rx_bytes %s" % (path, ifstats[0]))
        logger.info("%s rx_packets %s" % (path, ifstats[1]))
        logger.info("%s rx_errs %s" % (path, ifstats[2]))
        logger.info("%s rx_drop %s" % (path, ifstats[3]))
        logger.info("%s tx_bytes %s" % (path, ifstats[4]))
        logger.info("%s tx_packets %s" % (path, ifstats[5]))
        logger.info("%s tx_errs %s" % (path, ifstats[6]))
        logger.info("%s tx_drop %s" % (path, ifstats[7]))
    else:
        logger.error("fail to get domain interface statistics\n")
        return 1

    return 0
