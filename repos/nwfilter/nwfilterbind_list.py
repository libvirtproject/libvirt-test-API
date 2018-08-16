#!/usr/bin/env python

import time

from libvirt import libvirtError
from src import sharedmod
from utils import process, utils

required_params = ()
optional_params = {}


def check_filter_list(all_filter_list, logger):
    cmd = "ebtables -t nat -L"
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("%s failed: %s." % (cmd, ret.stdout))
        return False
    filter_num = 0
    for filter_list in all_filter_list:
        if filter_list.portDev() in ret.stdout:
            logger.info("%s in ebtables rule." % filter_list.portDev())
            filter_num += 1
    if filter_num == len(all_filter_list):
        return True
    else:
        return False


def nwfilterbind_list(params):
    logger = params['logger']

    if not utils.version_compare("libvirt-python", 4, 5, 0, logger):
        logger.info("Current libvirt-python don't support listAllNWFilterBindings().")
        return 0

    try:
        conn = sharedmod.libvirtobj['conn']
        all_filter_list = conn.listAllNWFilterBindings()
        time.sleep(3)
        if not check_filter_list(all_filter_list, logger):
            logger.error("FAIL: check nwfilterbind list failed.")
            return 1
        else:
            logger.info("PASS: check nwfilterbind list successful.")

    except libvirtError as e:
        logger.error("API error message: %s" % e.get_error_message())
        return 1

    return 0
