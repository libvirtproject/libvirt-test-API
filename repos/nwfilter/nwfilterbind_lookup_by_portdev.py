#!/usr/bin/env python

import time
import libvirt

from libvirt import libvirtError
from src import sharedmod
from utils import utils
from repos.domain import domain_common

required_params = ('portdev',)
optional_params = {}


def nwfilterbind_lookup_by_portdev(params):
    logger = params['logger']
    portdev = params['portdev']

    if not utils.version_compare("libvirt-python", 4, 5, 0, logger):
        logger.info("Current libvirt-python don't support nwfilterBindingLookupByPortDev().")
        return 0

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
        logger.error("API error message: %s, error code: %s." % (e.get_error_message(), e.get_error_code()))
        domain_common.get_last_error(logger)
        if e.get_error_code() == libvirt.VIR_ERR_NO_NWFILTER_BINDING and portdev == 'for-test':
            logger.info("PASS: negative test for VIR_ERR_NO_NWFILTER_BINDING flag.")
            return 0
        else:
            return 1

    return 0
