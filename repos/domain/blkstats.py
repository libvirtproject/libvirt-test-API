#!/usr/bin/evn python
# To test domain block device statistics

import time
import libxml2

import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ('guestname',)
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


def blkstats(params):
    """Domain block device statistic"""
    logger = params['logger']
    guestname = params['guestname']

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
        path = devs[0].content
        blkstats = domobj.blockStats(path)
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    if blkstats:
        # check_blkstats()
        logger.debug(blkstats)
        logger.info("%s rd_req %s" % (path, blkstats[0]))
        logger.info("%s rd_bytes %s" % (path, blkstats[1]))
        logger.info("%s wr_req %s" % (path, blkstats[2]))
        logger.info("%s wr_bytes %s" % (path, blkstats[3]))
    else:
        logger.error("fail to get domain block statistics\n")
        return 1

    return 0
