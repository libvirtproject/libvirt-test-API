#!/usr/bin/evn python
# To test blockJobAbort()

import libvirt
from libvirt import libvirtError

from utils.utils import parse_flags, get_rand_str, del_file, get_xml_value

IMG = '/var/lib/libvirt/images/test-api-blockjobabort'

required_params = ('guestname',)
optional_params = {'flags': None}


def block_job_abort(params):
    """domain blockJobAbort test function
    """
    logger = params['logger']
    guestname = params['guestname']
    flags = parse_flags(params, param_name='flags')
    logger.info("blockJobAbort flags : %s" % flags)

    conn = libvirt.open()
    domobj = conn.lookupByName(guestname)
    path = get_xml_value(domobj, "/domain/devices/disk/target/@dev")
    old_img = get_xml_value(domobj, "/domain/devices/disk/source/@file")
    logger.debug("old img: %s" % old_img)
    random_str = ''.join(get_rand_str())
    snapshot_xml = ("<domainsnapshot><name>%s</name><memory snapshot='no' file=''/>"
                    "</domainsnapshot>" % random_str)

    try:
        domobj.snapshotCreateXML(snapshot_xml, 16)
        domobj.blockCommit(path[0], None, None, 1048576, 4)
        domobj.blockJobAbort(path[0], flags)
        new_info = domobj.blockJobInfo(path[0], 0)

    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    if len(new_info) == 0:
        new_img = get_xml_value(domobj, "/domain/devices/disk/source/@file")
        logger.debug("new img: %s" % new_img)
        if flags == libvirt.VIR_DOMAIN_BLOCK_JOB_ABORT_PIVOT:
            if old_img[0] != new_img[0]:
                logger.error("FAIL: check blockJobAbort failed.")
                return 1
        else:
            if (old_img[0] + '.' + random_str) != new_img[0]:
                logger.error("FAIL: check blockJobAbort failed.")
                return 1
    else:
        logger.error("FAIL: blockJobAbort failed. info: %s" % new_info)
        return 1

    del_file((old_img[0] + '.' + random_str), logger)
    logger.info("PASS: check blockJobAbort successful.")

    return 0
