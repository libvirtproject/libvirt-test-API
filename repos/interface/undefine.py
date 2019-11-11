#!/usr/bin/env python

import libvirt
import os

from libvirt import libvirtError

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

    if check_undefine_interface(ifacename):
        logger.error("interface %s have been undefined" % ifacename)
        return 1

    try:
        conn = libvirt.open()
        ifaceobj = conn.interfaceLookupByName(ifacename)
        ifaceobj.undefine()
        if check_undefine_interface(ifacename):
            logger.info("undefine a interface is successful")
        else:
            logger.error("fail to check undefine interface")
            return 1
    except libvirtError as err:
        logger.error("API error message: %s, error code is %s"
                     % (err.get_error_message(), err.get_error_code()))
        logger.error("Fail to undefine a interface.")
        return 1

    return 0
