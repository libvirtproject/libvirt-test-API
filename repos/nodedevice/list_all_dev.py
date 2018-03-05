#!/usr/bin/env python

import os
import re
import libvirt
from libvirt import libvirtError
from utils import utils
from src import sharedmod

required_params = ('flags', )
optional_params = {}


def parse_flags(logger, params):
    flags = params['flags']
    logger.info("list all devices with flags: %s" % flags)

    ret = 0
    for flag in flags.split('|'):
        if flag == 'system':
            ret = ret | libvirt.VIR_CONNECT_LIST_NODE_DEVICES_CAP_SYSTEM
        elif flag == 'pci':
            ret = ret | libvirt.VIR_CONNECT_LIST_NODE_DEVICES_CAP_PCI_DEV
        elif flag == 'usb_dev':
            ret = ret | libvirt.VIR_CONNECT_LIST_NODE_DEVICES_CAP_USB_DEV
        elif flag == 'usb_interface':
            ret = ret | libvirt.VIR_CONNECT_LIST_NODE_DEVICES_CAP_USB_INTERFACE
        elif flag == 'net':
            ret = ret | libvirt.VIR_CONNECT_LIST_NODE_DEVICES_CAP_NET
        elif flag == 'scsi_host':
            ret = ret | libvirt.VIR_CONNECT_LIST_NODE_DEVICES_CAP_SCSI_HOST
        elif flag == 'scsi_target':
            ret = ret | libvirt.VIR_CONNECT_LIST_NODE_DEVICES_CAP_SCSI_TARGET
        elif flag == 'scsi':
            ret = ret | libvirt.VIR_CONNECT_LIST_NODE_DEVICES_CAP_SCSI
        elif flag == 'storage':
            ret = ret | libvirt.VIR_CONNECT_LIST_NODE_DEVICES_CAP_STORAGE
        elif flag == 'fc_host':
            ret = ret | libvirt.VIR_CONNECT_LIST_NODE_DEVICES_CAP_FC_HOST
        elif flag == 'vports':
            ret = ret | libvirt.VIR_CONNECT_LIST_NODE_DEVICES_CAP_VPORTS
        elif flag == 'scsi_generic':
            ret = ret | libvirt.VIR_CONNECT_LIST_NODE_DEVICES_CAP_SCSI_GENERIC
        elif flag == 'drm':
            ret = ret | libvirt.VIR_CONNECT_LIST_NODE_DEVICES_CAP_DRM
        elif flag == 'mdev':
            ret = ret | libvirt.VIR_CONNECT_LIST_NODE_DEVICES_CAP_MDEV
        elif flag == 'mdev_type':
            ret = ret | libvirt.VIR_CONNECT_LIST_NODE_DEVICES_CAP_MDEV_TYPES
        elif flag == 'ccw':
            ret = ret | libvirt.VIR_CONNECT_LIST_NODE_DEVICES_CAP_CCW_DEV
        else:
            logger.error("flag is illegal.")
            return -1
    return ret


def check_mdev(devs, logger):
    mdev_path = "/sys/bus/mdev/devices/"
    mdev_list = []
    for dev in devs:
        if "mdev" in dev.name():
            mdev_list.append(dev.name().strip('mdev_').replace('_', '-'))
    if not os.path.exists(mdev_path):
        if len(devs) == 0:
            logger.info("host don't support mdev.")
            return 0
        else:
            if len(mdev_list) != 0:
                logger.error("%s don't exist." % mdev_path)
                return 1
            else:
                logger.info("host don't support mdev.")
                return 0
    file_list = os.listdir(mdev_path)
    for mdev in mdev_list:
        if mdev in file_list:
            logger.info("check mdev %s successful." % mdev)
        else:
            logger.error("check mdev %s failed." % mdev)
            return 1

    return 0


def check_mdev_type(devs, logger):
    mdev_type_path = "/sys/class/mdev_bus/"
    path_list = []
    for dev in devs:
        if "pci_" in dev.name():
            tmp = dev.name().strip('pci_')
            tmp = re.sub("_", ":", tmp, 2)
            path_list.append(tmp.replace('_', '.'))
    if not os.path.exists(mdev_type_path):
        if len(devs) == 0:
            logger.info("host don't support mdev type.")
            return 0
        else:
            if len(path_list) != 0:
                logger.error("%s don't exist." % mdev_type_path)
                return 1
            else:
                logger.info("host don't support mdev type.")
                return 0
    for path in path_list:
        if os.path.exists(mdev_type_path + path):
            logger.info("check mdev type %s successful." % path)
        else:
            logger.error("check mdev type %s failed." % path)
            return 1

    return 0


def check_ccw(devs, logger):
    ccw_path = "/sys/bus/ccw/devices/"
    path_list = []

    if len(devs) == 0 and not os.path.exists(ccw_path):
        logger.info("host don't support ccw.")
        return 0

    for dev in devs:
        if "ccw_" in dev.name():
            tmp = dev.name().strip('ccw_')
            path_list.append(re.sub("_", ".", tmp, 2))
    for path in path_list:
        if os.path.exists(ccw_path + path):
            logger.info("check ccw %s successful." % path)
        else:
            logger.error("check ccw %s failed." % path)
            return 1

    return 0


def list_all_dev(params):
    """Check node deveice list"""
    logger = params['logger']
    flags = parse_flags(logger, params)
    if flags == -1:
        return 1

    try:
        conn = sharedmod.libvirtobj['conn']
        devs = conn.listAllDevices(flags)
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    flag = params['flags']
    if "mdev_type" in flag:
        if check_mdev_type(devs, logger):
            return 1
    elif "mdev" in flag:
        if check_mdev(devs, logger):
            return 1
    elif "ccw" in flag:
        if not utils.version_compare("libvirt-python", 3, 8, 0, logger):
            logger.info("Current libvirt-python don't support ccw dev.")
            return 0

        if check_ccw(devs, logger):
            return 1

    return 0
