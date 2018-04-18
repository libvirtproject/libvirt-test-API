#!/usr/bin/env python

from libvirt import libvirtError
from src import sharedmod
from utils import utils

from repos.snapshot.common import convert_flags

required_params = ('guestname', 'flags', )
optional_params = {}

SNAPSHOT_DIR = "ls /var/lib/libvirt/qemu/snapshot"
SNAPSHOT_LIST = "virsh snapshot-list %s|sed -n '3,$'p|awk '{print $1}'"
FLAGDICT = {0: "", 1: " --roots", 2: " --metadata", 4: " --leaves",
            8: " --no-leaves", 16: " --no-metadata", 32: " --inactive",
            64: " --active", 128: " --disk-only", 256: " --internal",
            512: " --external"}


def get_snapshot_list_virsh(*args):
    """ Get the snapshot name list through virsh command """

    (guestname, flaglist) = args
    flagstr = ""
    # Convert the flags that be passed to API to VIRSH flags
    for flag_key in flaglist:
        if int(flag_key) in FLAGDICT:
            flagstr += FLAGDICT.get(int(flag_key))
            guestname_flags = guestname + flagstr
    logger.info("Execute virsh snapshot-list" + flagstr)

    snapshot_list_virsh = []
    (status, output) = utils.exec_cmd(SNAPSHOT_LIST % guestname_flags,
                                      shell=True)
    if status:
        logger.error("Executing \"" + SNAPSHOT_LIST % guestname + "\" failed")
        logger.error(status)
        return 1
    else:
        snapshot_list_virsh = output[:-1]
        logger.info("Get snapshot name list via VIRSH: %s"
                    % snapshot_list_virsh)
        return snapshot_list_virsh


def compare_snapshot_list(*args):
    """ Compare two snapshot name list  whether have the same items """

    (snapshot_list1, snapshot_list2) = args
    if snapshot_list1 is None and snapshot_list2 is None:
        logger.info("The two snapshot lists are empty")
        return True

    if (snapshot_list1 is not None and snapshot_list2 is not None and
            len(snapshot_list1) == len(snapshot_list2)):
        list_len = len(snapshot_list1)
        snapshot_list1.sort()
        snapshot_list2.sort()
        for index in range(list_len):
            if snapshot_list1[index] != snapshot_list2[index]:
                logger.error("The two snapshot lists don't have the same")
                return False
        logger.info("The two snapshot lists have the same items")
        return True
    else:
        logger.error("The two lists length don't have the same")
        return False


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


def check_get_domain(dom, snapshot, logger):
    if snapshot.getDomain().XMLDesc() == dom.XMLDesc():
        return True
    logger.error("snapshot getDomain return wrong domain")
    logger.error("Expect: " + dom.XMLDesc())
    logger.error("Got: " + snapshot.getDomain().XMLDesc())
    return False


def check_get_connect(conn, snapshot, logger):
    if snapshot.getConnect().getURI() == conn.getURI():
        return True
    logger.error("snapshot getConnect return wrong connection")
    logger.error("Expect: " + conn.getURI())
    logger.error("Got: " + snapshot.getConnect().getURI())
    return False


def snapshot_list(params):
    """ List snapshots for a domain with filters"""

    global logger
    logger = params['logger']
    guestname = params['guestname']
    conn = sharedmod.libvirtobj['conn']
    domobj = conn.lookupByName(guestname)
    flags = params['flags']
    (flaglist, flagn) = convert_flags(flags, FLAGDICT, logger)

    try:
        logger.info("Flag list %s " % flaglist)
        logger.info("bitwise OR value of flags is %s" % flagn)
        snapshot_list_dir = get_snapshot_list_dir(guestname)

        # If domain doesn't have shapshot ,return 1
        if not domobj.hasCurrentSnapshot(0) and len(snapshot_list_dir) == 0:
            logger.error("The domain doesn't have any snapshot")
            return 1
        else:
            # Get the total number of domain's snapshot
            if domobj.snapshotNum(0) == len(snapshot_list_dir):
                logger.info("The total number of domain's snapshots is %s"
                            % domobj.snapshotNum(0))

            # Get the snapshot number with filters
            snapshotnum_filters = domobj.snapshotNum(flagn)
            logger.info("The number of domain's snapshots with filters is %s"
                        % snapshotnum_filters)

            # Get the snapshot name list of domain's snapshot
            snapshot_namelist_api = domobj.snapshotListNames(flagn)
            logger.info("Get snapshots name list via API: %s" %
                        snapshot_namelist_api)

            # Get all snapshot name from listAllSnapshots
            snapshot_list = domobj.listAllSnapshots(flagn)
            for snapshot_item in snapshot_list:
                logger.info("The snapshot's name:" + snapshot_item.getName())
                if not check_get_domain(domobj, snapshot_item, logger):
                    return 1
                if not check_get_connect(conn, snapshot_item, logger):
                    return 1

            # Check the two snapshot list is the same
            snapshot_namelist_virsh = get_snapshot_list_virsh(guestname,
                                                              flaglist)
            if compare_snapshot_list(snapshot_namelist_virsh,
                                     snapshot_namelist_api) and \
                    snapshotnum_filters == \
                    len(snapshot_namelist_api):
                logger.info("Successfully get snapshot name list")
                return 0
            else:
                logger.error("Failed to get snapshot name list through API")
                return 1

    except libvirtError as e:
        logger.error("API error message: %s" % e.get_error_message())
        return 1

    return 0
