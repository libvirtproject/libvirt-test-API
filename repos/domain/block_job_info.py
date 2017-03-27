#!/usr/bin/evn python
# To test blockJobInfo()

import lxml
import lxml.etree
import os

import libvirt
from libvirt import libvirtError

from utils import utils
from utils.utils import parse_flags

IMG = '/var/lib/libvirt/images/test-api-blockcopy'

required_params = ('guestname', 'flags',)
optional_params = {}


def get_path(dom):
    dom_xml = dom.XMLDesc(0)
    tree = lxml.etree.fromstring(dom_xml)
    return tree.xpath("/domain/devices/disk/target/@dev")


def del_img(img):
    if os.path.exists(img):
        cmd = 'rm -f %s' % (img)
        ret, out = utils.exec_cmd(cmd, shell=True)
        if ret:
            logger.error("delete img failed. cmd: %s, out: %s" % (cmd, out))
            return False

    return True


def block_job_info(params):
    """domain blockJobInfo test function
    """
    logger = params['logger']
    guestname = params['guestname']
    flags = parse_flags(params, param_name='flags')
    logger.info("blockJobInfo flags : %s" % flags)

    conn = libvirt.open()
    domobj = conn.lookupByName(guestname)
    path = get_path(domobj)

    blockcopy_xml = "<disk><source file='%s'/></disk>" % IMG
    logger.info("blockcopy xml: %s" % blockcopy_xml)
    bandwidth = 1048576
    logger.info("blockcopy bandwidth: %s" % bandwidth)

    try:
        old_info = domobj.blockJobInfo(path[0], flags)
        logger.info("before blockJobInfo: %s." % old_info)

        domobj.blockCopy(path[0], blockcopy_xml, {"bandwidth": bandwidth}, 0)
        new_info = domobj.blockJobInfo(path[0], flags)
        logger.info("after blockJobInfo: %s." % new_info)

        domobj.blockJobAbort(path[0])
        if not del_img(IMG):
            return 1

        if flags == libvirt.VIR_DOMAIN_BLOCK_JOB_INFO_BANDWIDTH_BYTES:
            if (len(old_info) == 0 and len(new_info) == 4 and
                    new_info['type'] == 2 and new_info['bandwidth'] == bandwidth):
                logger.info("PASS: get block job info success.")
            else:
                logger.error("FAIL: get block job info failed")
                return 1
        else:
            if (len(old_info) == 0 and len(new_info) == 4 and
                    new_info['type'] == 2 and new_info['bandwidth'] == bandwidth / (1024 * 1024)):
                logger.info("PASS: get block job info success.")
            else:
                logger.error("FAIL: get block job info failed")
                return 1

    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
