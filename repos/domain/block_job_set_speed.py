#!/usr/bin/evn python
# To test blockJobSetSpeed()

import libvirt

from libvirt import libvirtError
from utils import utils

IMG = '/var/lib/libvirt/images/test-api-blockjobsetspeed'

required_params = ('guestname', 'bandwidth',)
optional_params = {'flags': None}


def block_job_set_speed(params):
    """domain blockJobSetSpeed test function
    """
    logger = params['logger']
    guestname = params['guestname']
    bandwidth = params['bandwidth']
    flags = utils.parse_flags(params, param_name='flags')
    logger.info("blockJobSetSpeed flags : %s" % flags)

    conn = libvirt.open()
    domobj = conn.lookupByName(guestname)
    path = utils.get_xml_value(domobj, "/domain/devices/disk/target/@dev")

    blockcopy_xml = "<disk><source file='%s'/></disk>" % IMG
    logger.info("blockcopy xml: %s" % blockcopy_xml)

    try:
        if utils.isRelease('8', logger):
            domobj.blockCopy(path[0], blockcopy_xml, {}, 0)
        else:
            domobj.blockCopy(path[0], blockcopy_xml, None, 0)
        domobj.blockJobSetSpeed(path[0], int(bandwidth), flags)
        new_info = domobj.blockJobInfo(path[0], 1)
        logger.info("blockJobInfo: %s." % new_info)
        domobj.blockJobAbort(path[0])

        if not utils.del_file(IMG, logger):
            return 1

        if flags == libvirt.VIR_DOMAIN_BLOCK_JOB_SPEED_BANDWIDTH_BYTES:
            if new_info['bandwidth'] == int(bandwidth):
                logger.info("Pass: block job set speed successful.")
            else:
                logger.error("Fail: block job set speed failed.")
                return 1
        else:
            if new_info['bandwidth'] == (int(bandwidth) * 1024 * 1024):
                logger.info("Pass: block job set speed successful.")
            else:
                logger.error("Fail: block job set speed failed")
                return 1

    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    return 0
