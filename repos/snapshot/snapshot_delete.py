#!/usr/bin/env python

from libvirt import libvirtError

from src import sharedmod
from utils import utils
from repos.snapshot.common import convert_flags

required_params = ('guestname', 'flags', 'snapshotname',)
optional_params = {}

SNAPSHOT_DIR = "ls /var/lib/libvirt/qemu/snapshot"
FLAGDICT = {0: "no flag", 1: " --children", 2: " --metadata-only",
            4: " --children-only"}


def get_snapshot_list_dir(guestname):
    """ Get the snapshot list from snapshot dir """

    commandstr = SNAPSHOT_DIR + "/" + guestname + "|awk '{print $NF}'"
    logger.info("Execute command:" + commandstr)
    (status, output) = utils.exec_cmd(commandstr, shell=True)
    snapshot_list_dir = []
    if status:
        logger.error("Executing " + commandstr + " failed")
        logger.error(output)
        return False
    else:
        for i in range(len(output)):
            snapshot_list_dir.append(output[i][:-4])
        logger.info("Get snapshot name list under dir: %s"
                    % snapshot_list_dir)
        return snapshot_list_dir


def check_snapshot_dir(*args):
    """ Check if the snapshot' xml exits in snapshot dir """

    (flagn, snapshotname, snapshot_childrenname, snapshot_list_dir) = args
    # The passed flags include "metadata-only" or 0
    if (flagn == 0) or (flagn == 2):
        for item in snapshot_list_dir:
            if item != snapshotname:
                logger.info("Successfully delete snapshot")
                return True
            else:
                logger.error("Snapshot's xml still exits in snapshot dir")
                return False
    # The passed flags include "children"
    elif (flagn == 1) or (flagn == 3):
        for snapshot_child in snapshot_childrenname:
            if snapshot_child not in snapshot_list_dir and \
                    snapshotname not in snapshot_list_dir:
                logger.info("Snapshot %s 's children are ")
                return True
            else:
                logger.error("Snapshot's xml still exits in snapshot dir")
                return False
    # The passed flags include "children-only"
    elif (flagn == 4) or (flagn == 6):
        for snapshot_child in snapshot_childrenname:
            if snapshot_child not in snapshot_list_dir:
                logger.info("Snapshot %s 's children are" % snapshot_child)
                return True
            else:
                logger.error("Snapshot's xml still exits in snapshot dir")
                return False


def snapshot_delete(params):
    """ Delete a specified snapshot for a given guest """

    global logger
    logger = params['logger']
    guestname = params['guestname']
    conn = sharedmod.libvirtobj['conn']
    snapshotname = params['snapshotname']
    flags = params['flags']
    (flaglist, flagn) = convert_flags(flags, FLAGDICT, logger)

    try:

        logger.info("Flag list %s " % flaglist)
        logger.info("bitwise OR value of flags is %s" % flagn)

        domobj = conn.lookupByName(guestname)
        snapobj = domobj.snapshotLookupByName(snapshotname, 0)

        snapshot_childrenname = snapobj.listChildrenNames(0)
        snapshot_allchildren = snapobj.listAllChildren(0)
        logger.info("Snapshot's children are %s" % snapshot_childrenname)
        logger.info("List all children for snapshot %s" % snapshot_allchildren)

        if (flagn == 1) or (flagn == 3):
            logger.info("Delete snapshot %s and its children" % snapshotname)
            numchildern = snapobj.numChildren(0)
            logger.info("Snapshot has %d children", numchildern)
        elif (flagn == 4) or (flagn == 6):
            logger.info("Only delete snapshot %s 's children" % snapshotname)

        else:
            logger.info("Delete snapshot %s " % snapshotname)

        snapobj.delete(flagn)
        snapshot_list_dir = get_snapshot_list_dir(guestname)
        check_snapshot_dir(flagn, snapshotname, snapshot_childrenname,
                           snapshot_list_dir)

    except libvirtError, e:
        logger.error("API error message: %s" % e.message)
        return 1

    return 0
