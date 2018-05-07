#!/usr/bin/env python
# Reset a node device

import os
import re
import sys
import commands

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils, sriov, process

required_params = ('vf_num',)
optional_params = {}


def check_node_reset():
    """Check node device reset result, I have no idea how to check it now"""
    pass


def reset(params):
    """Reset a specific node device and return clean & certain status to it"""
    logger = params['logger']
    vf_num = params['vf_num']

    if not sriov.create_vf(vf_num, logger):
        logger.error("create vf fail.")
        return 1

    vf_addr = sriov.get_vfs_addr(vf_num, logger)
    kernel_version = utils.get_host_kernel_version()

    if 'el5' in kernel_version:
        cmd = "lspci -n |grep %s|awk '{print $3}'" % vf_addr
        logger.debug("cmd: %s" % cmd)
        ret = process.run(cmd, shell=True, ignore_status=True)
        if ret.exit_status != 0:
            logger.error("failed to get vendor product ID")
            return 1
        else:
            vendor_ID = ret.stdout.split(":")[0]
            product_ID = ret.stdout.split(":")[1]
            device_name = "pci_%s_%s" % (vendor_ID, product_ID)
    else:
        (dom, bus, slot_func) = vf_addr.split(":")
        (slot, func) = slot_func.split(".")
        device_name = "pci_0000_%s_%s_%s" % (bus, slot, func)

    conn = sharedmod.libvirtobj['conn']

    try:
        nodeobj = conn.nodeDeviceLookupByName(device_name)
        nodeobj.reset()
        logger.info("reset the node device")
        logger.info("the node %s device reset is successful" % device_name)
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("Error: fail to reset %s node device" % device_name)
        return 1

    return 0
