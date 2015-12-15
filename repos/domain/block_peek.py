#!/usr/bin/evn python
# To test domain block device peek

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

        logger.info("start to test block_peek.")
        logger.info("get the MBR's last byte of domain %s %s is:"
                    % (guestname, vdev))

        last_byte = domobj.blockPeek(vdev, 511, 1, flag)
        logger.info(last_byte)

        # compare with '\xaa'
        if last_byte == '\xaa':
            logger.info("Pass: the last byte is \\xaa")
        else:
            logger.error("Failed: the last byte is not \\xaa")
            logger.error("please make sure the guest is bootable")
            return 1

    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
