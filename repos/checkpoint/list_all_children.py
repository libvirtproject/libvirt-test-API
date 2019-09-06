#!/usr/bin/env python

import libvirt

from libvirt import libvirtError
from utils import utils

required_params = {'guestname', 'checkpoint_name'}
optional_params = {'flags': None}


def list_all_children(params):
    logger = params['logger']
    guestname = params['guestname']
    checkpoint_name = params['checkpoint_name']
    flag = utils.parse_flags(params)

    if not utils.version_compare('libvirt-python', 5, 6, 0, logger):
        logger.info("Current libvirt-python don't support listAllChildren().")
        return 0

    logger.info("Checkpoint name: %s" % checkpoint_name)
    logger.info("flag: %s" % flag)

    try:
        conn = libvirt.open()
        dom = conn.lookupByName(guestname)
        cp = dom.checkpointLookupByName(checkpoint_name)
        cp_lists = cp.listAllChildren(flag)
        for cp_list in cp_lists:
            logger.info("Checkpoint children list: %s" % cp_list.getName())
    except libvirtError as err:
        logger.error("API error message: %s" % err.get_error_message())
        return 1

    return 0
