#!/usr/bin/env python

import time

from libvirt import libvirtError
from src import sharedmod
from utils import utils

required_params = ('portdev',)
optional_params = {}


def nwfilterbind_portdev(params):
    logger = params['logger']
    portdev = params['portdev']

    if not utils.version_compare("libvirt-python", 4, 5, 0, logger):
        logger.info("Current libvirt-python don't support nwfilterbind.portDev().")
        return 0

    try:
        conn = sharedmod.libvirtobj['conn']
        nwfilterbind = conn.nwfilterBindingLookupByPortDev(portdev)
        portdev_api = nwfilterbind.portDev()
        time.sleep(3)
        logger.info("get port dev by api: %s" % portdev_api)
        portdev_xml = utils.get_xml_value(nwfilterbind, "/filterbinding/portdev/@name")
        logger.info("get port dev by xml: %s" % portdev_xml)
        if portdev_xml[0] == portdev_api and portdev_api == portdev:
            logger.info("PASS: get portdev successful.")
        else:
            logger.error("FAIL: get portdev failed.")
            return 1

    except libvirtError as e:
        logger.error("API error message: %s" % e.get_error_message())
        return 1

    return 0
