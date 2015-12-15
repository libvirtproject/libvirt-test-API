#!/usr/bin/evn python

import os
import re
import sys

import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ('guestname',)
optional_params = {}


def check_undefine_domain(guestname):
    """Check undefine domain result, if undefine domain is successful,
       guestname.xml will don't exist under /etc/libvirt/qemu/
    """
    path = "/etc/libvirt/qemu/%s.xml" % guestname
    if not os.access(path, os.R_OK):
        return True
    else:
        return False


def undefine(params):
    """Undefine a domain"""
    logger = params['logger']
    guestname = params['guestname']
    conn = sharedmod.libvirtobj['conn']

    domobj = conn.lookupByName(guestname)

    try:
        domobj.undefine()
        if check_undefine_domain(guestname):
            logger.info("undefine the domain is successful")
        else:
            logger.error("fail to check domain undefine")
            return 1
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
