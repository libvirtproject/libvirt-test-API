#!/usr/bin/env python

import os
import time
import lxml.etree

from libvirt import libvirtError
from src import sharedmod
from utils import utils

required_params = ('portdev',)
optional_params = {}


def nwfilterbind(params):
    logger = params['logger']
    portdev = params['portdev']
    logger.info("portdev: %s" % portdev)

    try:
        conn = sharedmod.libvirtobj['conn']
        nwfilterbind = conn.nwfilterBindingLookupByPortDev(portdev)

        nwfilterbind_c_pointer = nwfilterbind.c_pointer()
        logger.info("c_pointer: %s" % nwfilterbind_c_pointer)

        nwfilterbind_conn = nwfilterbind.connect()
        time.sleep(3)
        logger.info("nwfilterbind_conn: %s" % nwfilterbind_conn)
        logger.info("conn: %s" % conn)
        if nwfilterbind_conn == conn:
            logger.info("PASS: get connect successful.")
        else:
            logger.error("FAIL: get connect failed.")
            return 1
    except libvirtError as e:
        logger.error("API error message: %s" % e.get_error_message())
        return 1

    return 0
