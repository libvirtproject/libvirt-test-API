#!/usr/bin/env python
# Test nodedev numbers

import libvirt
import commands
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ()
optional_params = {}

#defined in src/node_device/node_device_hal.c
LIBVIRT_NODE_DEVICE_CAPS = [
    "system",
    "pci",
    "usb",
    "usb_device",
    "net",
    "scsi_host",
    "scsi",
    "storage",
    "scsi_generic"
]

BAD_CAPS = [
    None,  # During testing, 'None' here meaning no parameter
    123,
    [],
]


def check_dev_num_of_cap(dev, num_expect, logger):
    num = dev.numOfCaps()
    if num != num_expect:
        logger.error("numOfCaps doesn't match."
                     "numOfCaps %d, expect %d" % (num, num_expect))
        return False
    return True


def check_num_total(conn, num, logger):
    devs = conn.listAllDevices()
    if len(devs) == num:
        return True
    logger.error("Number don't match with listAllDevices."
                 " Expect %d, got %d" % (len(devs), num))
    return False


def check_num_cap(conn, num, cap, logger):
    devs = []
    devs_all = conn.listAllDevices()
    for dev in devs_all:
        if cap in dev.listCaps():
            devs.append(dev)
        # Call a sub test
        if not check_dev_num_of_cap(dev, len(dev.listCaps()), logger):
            return False
    if len(devs) == num:
        return True
    logger.error("Number don't match with listAllDevices."
                 " Expect %d, got %d, cap %s"
                 % (len(devs), num, cap))
    return False


def check_num_virsh(num, logger, cap=""):
    (ret, out) = commands.getstatusoutput('virsh nodedev-list --cap "%s"' % cap)
    if ret != 0:
        logger.error("virsh error: %s" % out)
    vir_num = len(out.split('\n')) - 1
    if num == vir_num:
        return True
    logger.error("Number don't match with virsh."
                 " Expect %d, got %d, cap: %s"
                 % (vir_num, num, cap))
    return False


def check_negative(conn, logger, negative_cap):
    try:
        if negative_cap is None:
            conn.numOfDevices()
        else:
            conn.numOfDevices(negative_cap)
    except TypeError as e:
        return True
    except libvirtError as e:
        return True
    except Exception as e:
        logger.error("Unexpected Exceptoin type " + str(e))
        return False
    logger.error("negative test failed with " + str(negative_cap))
    return False


def device_num(params):
    """Check node deveice number related APIs"""
    logger = params['logger']
    conn = sharedmod.libvirtobj['conn']

    try:
        num_total = conn.numOfDevices(None)
        logger.info("Number of node devices: %d" % num_total)
        if not check_num_total(conn, num_total, logger):
            return 1
        if not check_num_virsh(num_total, logger):
            return 1

        for cap in LIBVIRT_NODE_DEVICE_CAPS:
            num = conn.numOfDevices(cap)
            logger.info("Number of node devices with cap %s: %d" % (cap, num))
            if not check_num_cap(conn, num, cap, logger):
                return 1
            if not check_num_virsh(num, logger, cap):
                return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    for cap in BAD_CAPS:
        if not check_negative(conn, logger, cap):
            return 1

    return 0
