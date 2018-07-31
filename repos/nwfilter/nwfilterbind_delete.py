#!/usr/bin/env python

import os
import time

from libvirt import libvirtError
from src import sharedmod
from utils import process, utils

required_params = ('portdev',)
optional_params = {}


def check_ebtables_rule(portdev, logger):
    cmd = "ebtables -t nat -L"
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("%s failed: %s." % (cmd, ret.stdout))
        return False
    if portdev in ret.stdout:
        logger.error("%s still exist in ebtables rule." % portdev)
        return False
    else:
        logger.info("%s don't exist in ebtables rule." % portdev)
    return True


def nwfilterbind_delete(params):
    logger = params['logger']
    portdev = params['portdev']

    if not utils.version_compare("libvirt-python", 4, 5, 0, logger):
        logger.info("Current libvirt-python don't support nwfilterbind.delete().")
        return 0
    try:
        conn = sharedmod.libvirtobj['conn']
        nwfilterbind = conn.nwfilterBindingLookupByPortDev(portdev)
        nwfilterbind.delete()
        time.sleep(3)
        nwfilterbind_list = conn.listAllNWFilterBindings()
        if nwfilterbind in nwfilterbind_list:
            logger.error("nwfilterbind still exist.")
            return 1
        if not check_ebtables_rule(portdev, logger):
            logger.error("FAIL: check ebtables rule failed.")
            return 1
        else:
            logger.info("PASS: check ebtables rule successful.")

    except libvirtError as e:
        logger.error("API error message: %s" % e.get_error_message())
        return 1

    return 0
