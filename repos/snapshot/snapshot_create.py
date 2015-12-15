#!/usr/bin/env python

import time
import libvirt

from libvirt import libvirtError
from src import sharedmod
from utils import utils

required_params = ('guestname', 'flags', )
optional_params = {'snapshotname': '',
                   'xml': 'xmls/snapshot.xml',
                   }

QEMU_IMAGE_FORMAT = "qemu-img info %s |grep format |awk -F': ' '{print $2}'"
FLAGDICT = {0: "no flag", 1: " --redefine", 2: " --current", 4: " --no-metadata",
            8: " --halt", 16: " --disk-only", 32: " --reuse-external",
            64: " --quiesce", 128: " --atomic", 256: " --live"}


def check_domain_image(*args):
    """ Check the format of disk image if is qcow2 """

    (domobj, guestname) = args
    dom_xml = domobj.XMLDesc(0)
    disk_path = utils.get_disk_path(dom_xml)
    (status, output) = utils.exec_cmd(QEMU_IMAGE_FORMAT % disk_path,
                                      shell=True)
    if status:
        logger.error("Executing " + "\"" + QEMU_IMAGE_FORMAT % guestname +
                     "\"" + " failed")
        logger.error(output)
        return False
    else:
        img_format = output[0]
        if img_format == "qcow2":
            logger.info("The format of domain image is qcow2")
            return True
        else:
            logger.error("%s has a disk %s with type %s, \
                          only qcow2 supports internal snapshot" %
                         (guestname, disk_path, img_format))
            return False


def check_current_snapshot(domobj):
    """ Check the current snapshot info """

    try:
        if domobj.hasCurrentSnapshot(0):
            current_snapshot = domobj.snapshotCurrent(0)
            if current_snapshot.isCurrent(0):
                logger.info("The current snapshot name is %s " %
                            current_snapshot.getName())
                return True
            else:
                logger.error("Failed to get current snapshot")
                return False
    except libvirtError, e:
        logger.error("API error message: %s" % e.message)
        return 1

    return 0


def convert_flags(flags):
    """ Bitwise-OR of flags in conf and convert them to the readable flags """

    flaglist = []
    flagstr = ""
    logger.info("The given flags are %s " % flags)
    if '|' not in flags:
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
    logger.info("Create snapshot with flags:" + flagstr)

    return (flaglist, flagn)


def create_redefine_xml(*args):
    """ Get the creationTime and state from current snapshot xml , and create
    a new xml for snapshot-create with redefine and current flags.
    """

    (domobj, xmlstr) = args
    xmlcur = domobj.snapshotCurrent(0).getXMLDesc(0)
    xmltime = xmlcur[xmlcur.find("<creationTime>"):xmlcur.find
                     ("</creationTime>") + 15]
    xmlstate = xmlcur[xmlcur.find("<state>"):xmlcur.find
                      ("</state>") + 8]

    xmlstr = xmlstr[:17] + xmltime + "\n" + xmlstate + xmlstr[17:]
    logger.info("Redefine current snapshot using xml: %s" % xmlstr)
    return xmlstr


def check_created_snapshot(*args):
    """ Check domain and snapshot info after creating snapshot is complete
    ,so RHEL6.4 only support shutdown internel snapshot, and live external
    snapshot (with option "--disk-only"), not fully support no-metadata
    """

    (domobj, flagn, snapshotname) = args
    flagbin = bin(flagn)
    # The passed flags include "redefine"
    if flagbin[-1:] == "1":
        #Check redefined snapshot name is equal to current snapshot'name
        if domobj.snapshotCurrent(0).getName() == snapshotname:
            logger.info("Successfully redefine current snapshot")
            return True
        else:
            logger.error("Failed to redefine current snapshot")
            return False
    # The passed flags include "halt"
    elif flagbin[-4:-3] == "1":
        state = domobj.info()[0]
        expect_states = [libvirt.VIR_DOMAIN_SHUTOFF,
                         libvirt.VIR_DOMAIN_SHUTOFF_FROM_SNAPSHOT,
                         libvirt.VIR_DOMAIN_SHUTOFF_DESTROYED]

        if state in expect_states:
            logger.info("Successfully halt after snapshot is created")
            return True
        else:
            logger.error("Failed to halt after snapshot is created")
            return False
    # The passed flags include "disk-only"
    elif flagbin[-5:-4] == "1":
        snapobj = domobj.snapshotLookupByName(snapshotname, 0)
        if "snapshot='external'" in snapobj.getXMLDesc(0):
            logger.info("Successfully create disk-only snapshot")
            return True
        else:
            logger.error("Failed to create disk-only snapshot")
            return False
    else:
        return True


def snapshot_create(params):
    """ Create a snapshot for a given domain """

    global logger
    logger = params['logger']
    guestname = params['guestname']
    flags = params['flags']
    xmlstr = params['xml']
    conn = sharedmod.libvirtobj['conn']
    domobj = conn.lookupByName(guestname)
    (flaglist, flagn) = convert_flags(flags)
    snapshotname = ""

    #if snapshotname isn't given in test suit, use current time as snapshotname
    if not params.has_key('snapshotname'):
        snapshotname = str(int(time.time()))
        xmlstr = xmlstr.replace('SNAPSHOTNAME', str(int(time.time())))
    else:
        snapshotname = params.get('snapshotname')

    #Checking the format of its disk
    if not check_domain_image(domobj, guestname):
        logger.error("Checking failed")
        return 1

    logger.debug("%s snapshot xml:\n%s" % (guestname, xmlstr))

    try:
        logger.info("Flag list %s " % flaglist)
        logger.info("bitwise OR value of flags is %s" % flagn)

        #If given flags include redefine, call create_redefine_xml method
        if flagn % 2 == 1:
            xmlstr = create_redefine_xml(domobj, xmlstr)
            domobj.snapshotCreateXML(xmlstr, flagn)
        else:
            domobj.snapshotCreateXML(xmlstr, flagn)

        #Guarantee creating snapshot is complete before check
        time.sleep(5)

        if check_created_snapshot(domobj, flagn, snapshotname) and \
                check_current_snapshot(domobj):
            logger.info("Successfully create snapshot")
            return 0
        else:
            logger.error("Failed to create snapshot")
            return 1

    except libvirtError, e:
        logger.error("API error message: %s" % e.message)
        return 1

    return 0
