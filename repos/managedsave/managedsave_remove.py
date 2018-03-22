#!/usr/bin/env python
# Save domain as a statefile

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('guestname',)
optional_params = {}


def check_savefile_remove(*args):
    """Check if guest's managedsave file be removed """

    (guestname) = args
    cmds = "ls /var/lib/libvirt/qemu/save/%s" % guestname + ".save -lh"
    logger.info("Execute cmd  %s" % cmds)
    (status, output) = utils.exec_cmd(cmds, shell=True)
    if status != 0:
        logger.info("No managed save file")
        return True
    else:
        logger.error("managed save file exits")
        return False


def managedsave_remove(params):
    """Remove an existing managed save state file from a domain"""

    global logger
    logger = params['logger']
    guestname = params['guestname']

    conn = sharedmod.libvirtobj['conn']
    domobj = conn.lookupByName(guestname)

    if not domobj.hasManagedSaveImage(0) and check_savefile_remove(guestname):
        logger.error("Domain %s hasn't managedsave image" % guestname)
        return 1
    else:
        logger.info("Domain %s has managedsave image" % guestname)

    try:
        domobj.managedSaveRemove(0)
        # Check if domain has managedsave image
        if not domobj.hasManagedSaveImage(0) and \
           check_savefile_remove(guestname):
            logger.info("Domain %s's managedsave image has been removed"
                        % guestname)
        else:
            logger.error("Fail to remove managedsave domain")
            return 1

    except libvirtError as e:
        logger.error("API error message: %s, error code is %s" % (e.get_error_message(), e.get_error_code()))
        logger.error("Fail to managedsave %s domain" % guestname)
        return 1

    return 0
