#!/usr/bin/evn python
# To test domain block device statistics

import time
import libvirt

from libvirt import libvirtError
from src import sharedmod
from utils.utils import get_xml_value

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
        xml_path = "/domain/devices/disk/target/@dev"
        path = get_xml_value(domobj, xml_path)
        blkstats = domobj.blockStats(path[0])
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    if blkstats:
        # check_blkstats()
        logger.debug(blkstats)
        logger.info("%s rd_req %s" % (path[0], blkstats[0]))
        logger.info("%s rd_bytes %s" % (path[0], blkstats[1]))
        logger.info("%s wr_req %s" % (path[0], blkstats[2]))
        logger.info("%s wr_bytes %s" % (path[0], blkstats[3]))
    else:
        logger.error("fail to get domain block statistics\n")
        return 1

    return 0
