#!/usr/bin/env python
# To test domain's openGraphicsFD API

import time
import os

import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ('guestname', 'idx')
optional_params = {'flags': ''}


def parse_flags(flags):
    """ parse flags
    """
    if flags == 'skipauth':
        return libvirt.VIR_DOMAIN_OPEN_GRAPHICS_SKIPAUTH
    elif flags is None:
        return 0
    else:
        return -1


def check_guest_status(domobj):
    """ check guest current status
    """
    state = domobj.info()[0]
    if state == libvirt.VIR_DOMAIN_SHUTOFF or \
            state == libvirt.VIR_DOMAIN_SHUTDOWN:
        return False
    else:
        return True


def check_graphicsfd(fd):
    """ check graphicsfd
    """
    try:
        f = os.fdopen(fd)
        f.close()
    except OSError as err:
        return False
    return True


def open_graphicsfd(params):
    """ test openGraphicsFD API
    """
    logger = params['logger']
    guestname = params['guestname']
    idx = int(params['idx'])
    flags = parse_flags(params.get('flags'))

    if flags == -1:
        logger.error("invalid flags for openGraphicsFD: %s" % flags)
        return 1

    logger.info("the guestname is %s" % guestname)
    logger.info("the idx is %s" % idx)
    logger.info("the flags is %s" % flags)

    conn = sharedmod.libvirtobj['conn']

    domobj = conn.lookupByName(guestname)

    # Check domain status
    if check_guest_status(domobj):
        pass
    else:
        domobj.create()
        time.sleep(90)

    try:
        fd = domobj.openGraphicsFD(idx)

        if check_graphicsfd(fd):
            logger.info("check graphicsfd: success.")
        else:
            logger.error("check graphicsfd: failed.")
            return 1

    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    return 0
