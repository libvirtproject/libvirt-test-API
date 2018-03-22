#!/usr/bin/env python

import libvirt
from libvirt import libvirtError
from src import sharedmod

required_params = ('guestname',)
optional_params = {}


def job_info(params):
    """Test get domain job info
    """
    guestname = params['guestname']
    logger = params['logger']

    try:
        conn = sharedmod.libvirtobj['conn']
        domobj = conn.lookupByName(guestname)
        info = domobj.jobInfo()
        logger.info("job info: %s" % info)
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    if info[0] == libvirt.VIR_DOMAIN_JOB_NONE:
        logger.info("PASS: get domain job info ok.")
    else:
        logger.error("FAIL: get domain job info failed.")

    return 0
