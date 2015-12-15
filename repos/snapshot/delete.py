#!/usr/bin/env python

import os
import sys
import re

import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ('guestname', 'snapshotname',)
optional_params = {}

SNAPSHOT_DIR = "/var/lib/libvirt/qemu/snapshot"


def check_domain_state(conn, guestname, logger):
    """ check if the domain exists and in shutdown state as well """
    guest_names = conn.listDefinedDomains()

    if guestname not in guest_names:
        logger.error("%s is running or does not exist" % guestname)
        return False
    else:
        return True


def check_xml(guestname, snapshotname, expected_flag, logger):
    """ after deleting, check if appropriate xml file exists or not"""
    guest_snapshot_dir = os.path.join(SNAPSHOT_DIR, guestname)
    snapshot_entries = os.listdir(guest_snapshot_dir)
    if snapshotname + ".xml" in snapshot_entries and expected_flag == "exist":
        return True
    elif snapshotname + ".xml" in snapshot_entries and expected_flag == "noexist":
        return False
    elif snapshotname + ".xml" not in snapshot_entries and expected_flag == "exist":
        return False
    elif snapshotname + ".xml" not in snapshot_entries and expected_flag == "noexist":
        return True


def delete(params):
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

    if not check_xml(guestname, snapshotname, "exist", logger):
        logger.error("no snapshot %s exists" % snapshotname)
        logger.debug("not corresponding xml file in %s" % SNAPSHOT_DIR)
        return 1

    try:
        logger.info("delete a snapshot for %s" % guestname)
        domobj = conn.lookupByName(guestname)
        snapobj = domobj.snapshotLookupByName(snapshotname, 0)
        snapobj.delete(0)
        if not check_xml(guestname, snapshotname, "noexist", logger):
            logger.error("after deleting, the corresponding \
                         xmlfile still exists in %s" % SNAPSHOT_DIR)
            return 1
        else:
            logger.info("delete snapshot %s succeeded" % snapshotname)
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
