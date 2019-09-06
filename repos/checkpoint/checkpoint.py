#!/usr/bin/env python

import libvirt

from libvirt import libvirtError
from utils import utils

required_params = {'guestname', 'checkpoint_name'}
optional_params = {'flags': None}


def checkpoint(params):
    logger = params['logger']
    guestname = params['guestname']
    checkpoint_name = params['checkpoint_name']
    flag = utils.parse_flags(params)

    if not utils.version_compare('libvirt-python', 5, 6, 0, logger):
        logger.info("Current libvirt-python don't support checkpoint API.")
        return 0

    logger.info("Checkpoint name: %s" % checkpoint_name)
    try:
        conn = libvirt.open()
        dom = conn.lookupByName(guestname)
        cp = dom.checkpointLookupByName(checkpoint_name)
        if conn == cp.connect():
            logger.info("Check connect() successful.")
        else:
            logger.error("Check connect() failed.")
            return 1
        if dom == cp.domain():
            logger.info("Check domain() successful.")
        else:
            logger.info("Check domain() failed.")
            return 1
        if checkpoint_name == cp.getName():
            logger.info("Check getName() successful.")
        else:
            logger.error("Check getName() failed.")
            return 1
        if conn == cp.getConnect():
            logger.info("Check getConnect() successful.")
        else:
            logger.error("Check getConnect() failed.")
            return 1
        if dom == cp.getDomain():
            logger.info("Check getDomain() successful.")
        else:
            logger.error("Check getDomain() failed.")
            return 1
    except libvirtError as err:
        logger.error("API error message: %s" % err.get_error_message())
        return 1
    return 0
