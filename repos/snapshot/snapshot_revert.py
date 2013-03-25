#!/usr/bin/env python

import time

import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ('guestname', 'flags', 'snapshotname', )
optional_params = {}
FLAGDICT = {0:" --snapshotname", 1:" --running", 2:" --paused", 4:" --force"}

def check_domain_state(*args):
    """ check if the domain state after revert """

    (flagn, domobj, snapshot) = args
    state = domobj.info()[0]

    if snapshot.isCurrent(0):
        logger.info("Successfull revert to given snapshotname")

        # The passed flags include "running"
        if (flagn == 1) or (flagn == 5):
            logger.info("After reverting, change state to running")
            expect_states = [libvirt.VIR_DOMAIN_RUNNING,\
                             libvirt.VIR_DOMAIN_RUNNING_FROM_SNAPSHOT,\
                             libvirt.VIR_DOMAIN_RUNNING_BOOTED]
            if state in expect_states:
                logger.info("Successful revert.The domain state is running.")
                return True
            else:
                logger.error("Failed to revert.The domain state isn't running")
                return False
        # The passed flags include "paused"
        elif (flagn == 2) or (flagn == 6):
            expect_states = [libvirt.VIR_DOMAIN_PAUSED,\
                             libvirt.VIR_DOMAIN_PAUSED_FROM_SNAPSHOT,\
                             libvirt.VIR_DOMAIN_PAUSED_SNAPSHOT]
            if state in expect_states:
                logger.info("Successful revert.The domain state is paused.")
                return True
            else:
                logger.error("Failed to revert.The domain state isn't paused")
                return False
    else:
        logger.error("Failed to revert to given snapshotname ")
        return False

def convert_flags(flags):
    """ Bitwise-OR of flags in conf and convert them to the readable flags """

    flaglist = []
    flagstr = ""
    logger.info("The given flags are %s " % flags)
    if not '|' in flags:
        flagn = int(flags)
        flaglist.append(flagn)
    else:
        # bitwise-OR of flags of create-snapshot
        flaglist = flags.split('|')
        flagn = 0
        for flag in flaglist:
            flagn |= int(flag)

    # Convert the flags in conf file to readable flag
    for flag_key in flaglist:
        if FLAGDICT.has_key(int(flag_key)):
            flagstr += FLAGDICT.get(int(flag_key))
    logger.info("Revert snapshot with flags:" + flagstr)

    return (flaglist, flagn)

def snapshot_revert(params):
    """ snapshot revert a snapshot for a given domain """

    global logger
    logger = params['logger']
    guestname = params['guestname']
    conn = sharedmod.libvirtobj['conn']
    domobj = conn.lookupByName(guestname)
    snapshotname = params['snapshotname']
    flags = params ['flags']
    (flaglist, flagn) = convert_flags(flags)

    try:
        logger.info("Flag list %s " % flaglist)
        logger.info("bitwise OR value of flags is %s" % flagn)

        logger.info("Revert a snapshot for %s" % guestname)
        snapshot = domobj.snapshotLookupByName(snapshotname, 0)
        domobj.revertToSnapshot(snapshot, flagn)
        # Guarantee revert is complete before check domain state
        time.sleep(10)
        check_domain_state(flagn, domobj, snapshot)
    except libvirtError, e:
        logger.error("API error message: %s" % e.message)
        return 1

    return 0
