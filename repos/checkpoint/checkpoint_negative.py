#!/usr/bin/env python

import libvirt

from libvirt import libvirtError
from utils import utils

required_params = {'guestname', 'checkpoint_name', 'flags'}
optional_params = {}


def checkpoint_negative(params):
    logger = params['logger']
    guestname = params['guestname']
    checkpoint_name = params['checkpoint_name']
    flags = params['flags']

    if not utils.version_compare('libvirt-python', 5, 6, 0, logger):
        logger.info("Current libvirt-python don't support checkpoint API.")
        return 0

    logger.info("Checkpoint name: %s" % checkpoint_name)
    logger.info("Flags: %s" % flags)

    try:
        conn = libvirt.open()
        dom = conn.lookupByName(guestname)
        cp = dom.checkpointLookupByName(checkpoint_name)
        if flags == 'invalid':
            cp.__del__()
            cp.getName()
        elif flags == 'no_domain':
            cp.getParent()
    except libvirtError as err:
        logger.error("API error message: %s" % err.get_error_message())
        if flags == 'invalid' and err.get_error_code() == 102:
            logger.info("Negative test PASS: test VIR_ERR_INVALID_DOMAIN_CHECKPOINT successful.")
        elif flags == 'no_domain' and err.get_error_code() == 103:
            logger.info("Negative test PASS: test VIR_ERR_NO_DOMAIN_CHECKPOINT successful.")
        else:
            logger.error("Negative test FAIL: error code: %s" % err.get_error_code())
            return 1
    return 0
