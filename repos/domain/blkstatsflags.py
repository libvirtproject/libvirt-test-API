#!/usr/bin/evn python
# To test domain block device statistics with flags

import time
import libxml2

import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ('guestname', 'flags')
optional_params = {}


def check_guest_status(domobj):
    """Check guest current status"""
    state = domobj.info()[0]
    if state == libvirt.VIR_DOMAIN_SHUTOFF or \
        state == libvirt.VIR_DOMAIN_SHUTDOWN:
    # add check function
        return False
    else:
        return True


def check_blkstats():
    """Check block device statistic result"""
    pass


def blkstatsflags(params):
    """Domain block device statistic"""
    logger = params['logger']
    guestname = params['guestname']
    flags = int(params['flags'])

    conn = sharedmod.libvirtobj['conn']

    domobj = conn.lookupByName(guestname)

    # Check domain block status
    if check_guest_status(domobj):
        pass
    else:
        domobj.create()
        time.sleep(90)
    try:
        xml = domobj.XMLDesc(0)
        doc = libxml2.parseDoc(xml)
        cont = doc.xpathNewContext()
        devs = cont.xpathEval("/domain/devices/disk/target/@dev")

        for dev in devs:
            path = dev.content
            blkstats = domobj.blockStatsFlags(path, flags)
            # check_blkstats()
            logger.debug(blkstats)
            for entry in blkstats.keys():
                logger.info("%s %s %s" % (path, entry, blkstats[entry]))

    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
