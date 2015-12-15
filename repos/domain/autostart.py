#!/usr/bin/evn python
# To test domain autostart

import os
import re
import sys

import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ('guestname', 'autostart',)
optional_params = {}


def check_guest_autostart(*args):
    """Check domain start automatically result, if setting domain is
       successful, guestname.xml will exist under
       /etc/libvirt/{hypervisor}/autostart/
    """
    (guestname, hypervisor, flag, logger) = args
    if 'xen' in hypervisor:
        domxml = "/etc/%s/auto/%s" % (hypervisor, guestname)
    else:
        domxml = "/etc/libvirt/%s/autostart/%s.xml" % (hypervisor, guestname)
    logger.debug("guest xml file is: %s" % domxml)

    if flag == 1:
        if os.access(domxml, os.F_OK):
            return True
        else:
            return False
    elif flag == 0:
        if not os.access(domxml, os.F_OK):
            return True
        else:
            return False
    else:
        return False


def autostart(params):
    """Set domain autostart capability"""
    logger = params['logger']
    guestname = params['guestname']
    autostart = params['autostart']

    flag = -1
    if autostart == "enable":
        flag = 1
    elif autostart == "disable":
        flag = 0
    else:
        logger.error("Error: autostart value is invalid")
        return 1

    conn = sharedmod.libvirtobj['conn']
    domobj = conn.lookupByName(guestname)
    uri = conn.getURI()

    try:
        domobj.setAutostart(flag)
        if check_guest_autostart(guestname, uri.split(":")[0], flag, logger):
            logger.info("current %s autostart: %s" %
                        (guestname, domobj.autostart()))
            logger.info("executing autostart operation is successful")
        else:
            logger.error("Error: fail to check autostart domain")
            return 1
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        logger.error("Error: fail to autostart %s domain" % guestname)
        return 1

    return 0
