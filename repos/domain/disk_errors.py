#!/usr/bin/env python
# get and check errors on block devices

import time
import libvirt
from libvirt import libvirtError

from src import sharedmod
from repos.domain import domain_common

required_params = ('guestname', 'xml')
optional_params = {'diskpath': '/var/lib/libvirt/images/libvirt-test-api',}


def disk_errors(params):
    """get and check errors on block devices is correct"""
    logger = params['logger']
    guestname = params['guestname']
    xmlstr = params['xml']

    conn = sharedmod.libvirtobj['conn']
    domain_common.guest_clean(conn, guestname, logger)

    try:
        logger.info("define and start guest.")
        domobj = conn.defineXML(xmlstr)
        domobj.create()
        time.sleep(10)
        error_list = domobj.diskErrors()
    except libvirtError, e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    # error_list:
    #     0 : no error
    #     1 : unspecified I/O error
    #     2 : no space left on the device
    logger.info("error_list: %s" % error_list)
    if error_list['vda'] != 1:
        logger.error("Fail: error msg is not correct.")
        return 1
    else:
        logger.info("PASS: error msg is correct.")
    return 0


def disk_errors_clean(params):
    logger = params['logger']
    guestname = params['guestname']
    conn = sharedmod.libvirtobj['conn']
    domain_common.guest_clean(conn, guestname, logger)
