#!/usr/bin/env python
# Re-attach a node device to host

import re
import time

from libvirt import libvirtError

from src import sharedmod
from utils import utils, sriov, process

required_params = ('vf_num',)
optional_params = {}


def reattach(params):
    """Reattach a specific node device and removed it
       from pci-stub driver, argument 'params' is a dictionary type
       and includes 'vf_num' key
    """
    logger = params['logger']
    vf_num = params['vf_num']

    if not sriov.create_vf(vf_num, logger):
        logger.error("create vf fail.")
        return 1

    vf_addr = sriov.get_vfs_addr(vf_num, logger)
    original_driver = sriov.get_vf_driver(vf_addr, logger)
    logger.info("original_driver: %s" % original_driver)

    kernel_version = utils.get_host_kernel_version()
    hypervisor = utils.get_hypervisor()
    pciback = ''
    if hypervisor == 'kvm':
        pciback = 'pci-stub'
    if hypervisor == 'xen':
        pciback = 'pciback'

    if utils.version_compare("libvirt-python", 3, 9, 0, logger):
        pciback = 'vfio-pci'

    if 'el5' in kernel_version:
        cmd = "lspci -n |grep %s|awk '{print $3}'" % vf_addr
        logger.debug("cmd: %s" % cmd)
        ret = process.run(cmd, shell=True, ignore_status=True)
        if ret.exit_status != 0:
            logger.error("failed to get vendor product ID")
            return 1
        else:
            vendor_ID = ret.stdout.split(":")[0]
            product_ID = re.stdout.split(":")[1]
            device_name = "pci_%s_%s" % (vendor_ID, product_ID)
    else:
        (dom, bus, slot_func) = vf_addr.split(":")
        (slot, func) = slot_func.split(".")
        device_name = "pci_0000_%s_%s_%s" % (bus, slot, func)

    logger.debug("the name of the pci device is: %s" % device_name)

    conn = sharedmod.libvirtobj['conn']

    try:
        nodeobj = conn.nodeDeviceLookupByName(device_name)
        nodeobj.reAttach()
        logger.info("reattach the node device")
        time.sleep(5)
        current_driver = sriov.get_vf_driver(vf_addr, logger)
        logger.info("current_driver: %s" % current_driver)
        if original_driver == pciback and current_driver != pciback:
            logger.info("the node %s device reattach is successful"
                        % device_name)
        else:
            logger.info("the node %s device reattach is failed" % device_name)
            return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    return 0
