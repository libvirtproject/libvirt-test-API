#!/usr/bin/evn python

import os
import re
import sys

import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ('guestname',)
optional_params = {'flags': 'none'}


def parse_flags(logger, params):
    flags = params.get('flags', 'none')
    logger.info('undefine with flags :%s' % flags)
    if flags == 'none':
        return None
    ret = 0
    for flag in flags.split('|'):
        if flag == 'managed_save':
            ret = ret | libvirt.VIR_DOMAIN_UNDEFINE_MANAGED_SAVE
        elif flag == 'snapshots_metadata':
            ret = ret | libvirt.VIR_DOMAIN_UNDEFINE_SNAPSHOTS_METADATA
        elif flag == 'nvram':
            ret = ret | libvirt.VIR_DOMAIN_UNDEFINE_NVRAM
        else:
            logger.error('illegal flags')
            return -1
    return ret


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
    flags = parse_flags(logger, params)

    if flags == -1:
        return 1

    domobj = conn.lookupByName(guestname)

    try:
        if flags is None:
            domobj.undefine()
        else:
            domobj.undefineFlags(flags)

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
