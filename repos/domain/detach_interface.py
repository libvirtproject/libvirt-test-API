#!/usr/bin/env python
# Detach interface from domain

import os
import re
import sys
import time

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('guestname', 'macaddr', 'nicdriver',)
optional_params = {'ifacetype': 'network',
                   'network': 'default',
                   'xml': 'xmls/nic.xml',
                   }


def check_detach_interface(num1, num2):
    """Check detach interface result via simple interface number
       comparison
    """
    if num2 < num1:
        return True
    else:
        return False


def detach_interface(params):
    """Detach a interface to domain from xml"""
    logger = params['logger']
    guestname = params['guestname']
    macaddr = params['macaddr']
    nicdriver = params['nicdriver']
    xmlstr = params['xml']

    macs = utils.get_dom_mac_addr(guestname)
    mac_list = macs.split("\n")
    logger.debug("mac address: \n%s" % macs)

    conn = sharedmod.libvirtobj['conn']
    domobj = conn.lookupByName(guestname)

    logger.debug("interface xml:\n%s" % xmlstr)

    iface_num1 = utils.dev_num(guestname, "interface")
    logger.debug("original interface number: %s" % iface_num1)

    try:
        domobj.detachDevice(xmlstr)
        iface_num2 = utils.dev_num(guestname, "interface")
        logger.debug("update interface number to %s" % iface_num2)
        if check_detach_interface(iface_num1, iface_num2):
            logger.info("current interface number: %s" % iface_num2)
        else:
            logger.error("fail to detach a interface to guest: %s" %
                         iface_num2)
            return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("detach the interface from guest %s" % guestname)
        return 1

    return 0
