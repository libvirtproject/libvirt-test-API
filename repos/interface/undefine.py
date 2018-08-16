#!/usr/bin/env python

import os

from libvirt import libvirtError

from src import sharedmod

required_params = ('ifacename',)
optional_params = {}


def check_undefine_interface(ifacename):
    """Check undefining interface result, if undefine interface is successful,
       ifcfg-ifacename will not exist under /etc/sysconfig/network-scripts/
    """
    path = "/etc/sysconfig/network-scripts/ifcfg-%s" % ifacename
    if not os.access(path, os.R_OK):
        return True
    else:
        return False


def undefine(params):
    """Undefine a specific interface"""
    global logger
    logger = params['logger']
    ifacename = params['ifacename']
    conn = sharedmod.libvirtobj['conn']

    if check_undefine_interface(ifacename):
        logger.error("interface %s have been undefined" % ifacename)
        return 1

    ifaceobj = conn.interfaceLookupByName(ifacename)

    try:
        ifaceobj.undefine()
        if check_undefine_interface(ifacename):
            logger.info("undefine a interface is successful")
        else:
            logger.error("fail to check undefine interface")
            return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("fail to undefine a interface")
        return 1

    return 0
