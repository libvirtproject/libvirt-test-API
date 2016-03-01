#!/usr/bin/evn python
# To test domain block device peek

import time
import libxml2
import libvirt
from libvirt import libvirtError
from utils import utils
import binascii

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


def block_peek(params):
    """domain block peek test function
    """
    logger = params['logger']
    guestname = params['guestname']
    flag = 0

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
        vdevs = cont.xpathEval("/domain/devices/disk/target/@dev")
        vdev = vdevs[0].content
        diskpaths = cont.xpathEval("/domain/devices/disk/source/@file")
        diskpath = diskpaths[0].content

        logger.info("get the MBR's first byte of domain %s %s."
                    % (guestname, vdev))
        first_byte = domobj.blockPeek(vdev, 0, 1, flag)

        cmd = "hexdump %s -n 1 -s 0 -e \'1/1 \"%s \"\'" % (diskpath, "%02x")
        status, ret = utils.exec_cmd(cmd, shell=True)
        if status:
            return 1

        logger.info("cmd: %s" % cmd)
        logger.info("result: %s" % ret[0].strip())
        if ret[0].strip() == binascii.b2a_hex(first_byte):
            logger.info("Pass: hexdump: %s, api: %s"
                        % (ret[0].strip(), binascii.b2a_hex(first_byte)))
        else:
            logger.error("Failed: hexdump: %s, api: %s"
                         % (ret[0].strip(), binascii.b2a_hex(first_byte)))
            logger.error("please make sure the guest is bootable")
            return 1

    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
