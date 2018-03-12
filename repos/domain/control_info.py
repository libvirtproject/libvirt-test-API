#!/usr/bin/env python

import libvirt
from libvirt import libvirtError
from src import sharedmod

required_params = ('guestname',)
optional_params = {}


def control_info(params):
    """Test get domain control info
    """
    guestname = params['guestname']
    logger = params['logger']

    try:
        conn = sharedmod.libvirtobj['conn']
        domobj = conn.lookupByName(guestname)
        info = domobj.controlInfo()
        logger.info("control info: %s" % info)
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    if (info[0] == libvirt.VIR_DOMAIN_CONTROL_OK and
            info[1] == libvirt.VIR_DOMAIN_CONTROL_ERROR_REASON_NONE and
            info[2] == 0):
        logger.info("PASS: get domain control info ok.")
    else:
        logger.error("FAIL: get domain control info failed.")

    return 0
