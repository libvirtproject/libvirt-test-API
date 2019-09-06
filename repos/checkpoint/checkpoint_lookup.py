#!/usr/bin/env python

import libvirt

from libvirt import libvirtError
from utils import utils

required_params = {'guestname', 'checkpoint_name'}
optional_params = {}


def checkpoint_lookup(params):
    logger = params['logger']
    guestname = params['guestname']
    checkpoint_name = params.get('checkpoint_name', None)

    logger.info("Checkpoint name: %s" % checkpoint_name)
    if not utils.version_compare('libvirt-python', 5, 6, 0, logger):
        logger.info("Current libvirt-python don't support checkpointLookupByName().")
        return 0

    try:
        conn = libvirt.open()
        dom = conn.lookupByName(guestname)
        cp = dom.checkpointLookupByName(checkpoint_name, 0)
    except libvirtError as err:
        logger.error("API error message: %s" % err.get_error_message())
        return 1

    # check checkpoint
    if cp.getName() == checkpoint_name:
        logger.info("PASS: check checkpoint name successful.")
        return 0
    else:
        logger.error("FAIL: check checkpoint name failed.")
        return 1
