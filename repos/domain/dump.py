#!/usr/bin/env python
# To test core dump of a domain

import os
import time
import libvirt

from libvirt import libvirtError
from utils import utils, process

required_params = ('guestname', 'file')
optional_params = {}


def check_guest_status(domobj, logger):
    """Check guest current status"""
    state = domobj.info()[0]
    logger.info("current guest status: %s" % state)
    if state == libvirt.VIR_DOMAIN_SHUTOFF or state == libvirt.VIR_DOMAIN_SHUTDOWN:
        return False
    else:
        return True


def check_dump(dump_file, logger):
    """check whether core dump file is generated"""
    if os.access(dump_file, os.R_OK):
        logger.info("%s is existing." % dump_file)
        return 0
    else:
        logger.error("%s is NOT existing!!!" % dump_file)
        return 1


def dump(params):
    """ Test coreDump() API
    """
    logger = params['logger']
    guestname = params['guestname']
    dump_file = params['file']

    if os.path.exists(dump_file):
        logger.info("%s is already existing, remove it." % dump_file)
        os.remove(dump_file)

    try:
        conn = libvirt.open()
        domobj = conn.lookupByName(guestname)
        if not check_guest_status(domobj, logger):
            logger.error("Please check guest status.")
            return 1
        logger.info("dump to: %s" % dump_file)
        domobj.coreDump(dump_file, 0)
        time.sleep(5)
        ret = check_dump(dump_file, logger)
        if ret:
            logger.error("check core dump failed.")
            return 1
        logger.info("check core dump successfully.")
        return 0
    except libvirtError as err:
        logger.error("API error message: %s, error code: %s"
                     % (err.get_error_message(), err.get_error_code()))
        return 1
    finally:
        if os.path.exists(dump_file):
            logger.info("remove dump file: %s" % dump_file)
            os.remove(dump_file)
