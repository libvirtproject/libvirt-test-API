#!/usr/bin/evn python
# undefine a network

import time
import os
import re
import sys

import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ('networkname',)
optional_params = {}


def check_network_undefine(networkname):
    """Check undefine network result, if undefine network is successful,
       networkname.xml willn't exist under /etc/libvirt/qemu/networks/,
       if will return True, otherwise, return False
    """
    path = "/etc/libvirt/qemu/networks/%s.xml" % networkname
    if not os.access(path, os.R_OK):
        return True
    else:
        return False


def undefine(params):
    """Undefine a network"""
    logger = params['logger']
    networkname = params['networkname']

    conn = sharedmod.libvirtobj['conn']

    if check_network_undefine(networkname):
        logger.error("the network %s is undefine" % networkname)
        return 1

    net_num1 = conn.numOfDefinedNetworks()
    logger.info("original network define number: %s" % net_num1)

    try:
        netobj = conn.networkLookupByName(networkname)
        netobj.undefine()
        net_num2 = conn.numOfDefinedNetworks()
        if check_network_undefine(networkname) and net_num2 < net_num1:
            logger.info("current network define number: %s" % net_num2)
            logger.info("undefine %s network is successful" % networkname)
        else:
            logger.error("the network %s is still define" % networkname)
            return 1
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        logger.error("fail to undefine a network")
        return 1

    return 0
