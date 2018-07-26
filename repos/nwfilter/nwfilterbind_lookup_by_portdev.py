#!/usr/bin/env python

import os
import time

from libvirt import libvirtError
from src import sharedmod
from utils import process

required_params = ('portdev',)
optional_params = {}


def nwfilterbind_lookup_by_portdev(params):
    logger = params['logger']
    portdev = params['portdev']

    logger.info("port dev: %s" % portdev)
    try:
        conn = sharedmod.libvirtobj['conn']
        nwfilterbind = conn.nwfilterBindingLookupByPortDev(portdev)
        time.sleep(3)
        logger.info("get port dev by api: %s" % nwfilterbind.portDev())
        if nwfilterbind.portDev() == portdev:
            logger.info("PASS: check nwfilterbind successful.")
        else:
            logger.error("FAIL: check nwfilterbind failed.")
            return 1
    except libvirtError as e:
        logger.error("API error message: %s" % e.get_error_message())
        return 1

    return 0
