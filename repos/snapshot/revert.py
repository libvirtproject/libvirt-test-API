#!/usr/bin/env python

import os
import sys
import re

import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ('guestname', 'snapshotname',)
optional_params = {}


def check_domain_state(conn, guestname, logger):
    """ check if the domain exists and in shutdown state as well """
    guest_names = conn.listDefinedDomains()

    if guestname not in guest_names:
        logger.error("%s is running or does not exist" % guestname)
        return False
    else:
        return True


def revert(params):
    """ snapshot revert a snapshot for a given guest,
        this case could be with other cases togerther to
        check the functionality of snapshot
    """
    logger = params['logger']
    guestname = params['guestname']
    snapshotname = params['snapshotname']

    conn = sharedmod.libvirtobj['conn']

    logger.info("checking if the guest is poweroff")
    if not check_domain_state(conn, guestname, logger):
        logger.error("checking failed")
        return 1

    try:
        logger.info("revert a snapshot for %s" % guestname)
        domobj = conn.lookupByName(guestname)
        snap = domobj.snapshotLookupByName(snapshotname, 0)
        domobj.revertToSnapshot(snap, 0)
        logger.info("revert snapshot succeeded")
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
