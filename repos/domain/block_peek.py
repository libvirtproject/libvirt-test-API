#!/usr/bin/evn python
# To test domain block device peek

import time
import libvirt
import binascii

from libvirt import libvirtError
from src import sharedmod
from utils import utils
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
        xml_path = "/domain/devices/disk/target/@dev"
        vdev = get_xml_value(domobj, xml_path)

        xml_path = "/domain/devices/disk/source/@file"
        diskpath = get_xml_value(domobj, xml_path)

        logger.info("get the MBR's first byte of domain %s %s."
                    % (guestname, vdev))
        first_byte = domobj.blockPeek(vdev[0], 0, 1, flag)

        cmd = "hexdump %s -n 1 -s 0 -e \'1/1 \"%s \"\'" % (diskpath[0], "%02x")
        status, ret = utils.exec_cmd(cmd, shell=True)
        if status:
            return 1

        logger.info("cmd: %s" % cmd)
        logger.info("result: %s" % ret[0].strip())
        api_first_byte = utils.decode_to_text(binascii.b2a_hex(first_byte))
        logger.info("hexdump: %s, api: %s" % (ret[0].strip(), api_first_byte))
        if ret[0].strip() != api_first_byte:
            logger.error("please make sure the guest is bootable")
            return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    return 0
