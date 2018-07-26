#!/usr/bin/env python

import os
import time

from libvirt import libvirtError
from src import sharedmod
from utils import utils

required_params = ('portdev',)
optional_params = {}


def nwfilterbind_filter_name(params):
    logger = params['logger']
    portdev = params['portdev']

    try:
        conn = sharedmod.libvirtobj['conn']
        nwfilterbind = conn.nwfilterBindingLookupByPortDev(portdev)
        filter_name = nwfilterbind.filterName()
        time.sleep(3)
        logger.info("get filter name by api: %s" % filter_name)
        filter_name_xml = utils.get_xml_value(nwfilterbind, "/filterbinding/filterref/@filter")
        logger.info("get filter name by xml: %s" % filter_name_xml)
        if filter_name_xml[0] != filter_name:
            logger.error("FAIL: get filter name failed.")
            return 1
        else:
            logger.info("PASS: get filter name successful.")

    except libvirtError as e:
        logger.error("API error message: %s" % e.get_error_message())
        return 1

    return 0
