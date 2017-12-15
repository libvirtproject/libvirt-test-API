#!/usr/bin/env python
# Loop attach/detach a disk through xml on domain using all
# supported flags

import os
import re
import sys
import time
import commands

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

from repos.domain.start import start

config_dir = '/etc/libvirt/qemu/'

required_params = ('guestname',
                   'imageformat',
                   'hddriver',)
optional_params = {'diskpath': '/var/lib/libvirt/images/attacheddisk',
                   'xml': 'xmls/disk.xml',
                   }


def create_image(diskpath, seeksize, imageformat, logger):
    """Create a image file"""
    disk_create = "qemu-img create -f %s %s %sG" % \
        (imageformat, diskpath, seeksize)
    logger.debug("the command line of creating disk images is '%s'" %
                 disk_create)

    (status, message) = commands.getstatusoutput(disk_create)
    if status != 0:
        logger.debug(message)
        return 1

    return 0


def check_disk(num1, num2):
    """Check detach disk result via simple disk number
       comparison
    """
    if num2 < num1:
        return 0
    elif num2 == num1:
        return 1
    else:
        return 2


def check_persistent(guestname, target):
    """Check target disk in domain config xml
    """
    config_xml = config_dir + guestname + '.xml'
    f = open(config_xml, 'r')
    xmlstr = f.read()

    if re.search(target, xmlstr):
        return True
    else:
        return False


def detach_disk(domobj, guestname, state, xmlstr, flags, target, disk_num1,
                logger):
    """Detach a disk with xml from domain with flags"""
    logger.info("detach disk with flags: %s" % flags)
    if state == libvirt.VIR_DOMAIN_SHUTOFF:
        if flags == 1 or flags == 3:
            try:
                domobj.detachDeviceFlags(xmlstr, int(flags))
                logger.error("this should fail")
                return 1
            except libvirtError, e:
                logger.error("libvirt call failed: " + str(e))
                logger.info("live detach fail on shutoff domain is expected")
                return 0

        else:
            try:
                domobj.detachDeviceFlags(xmlstr, int(flags))
                config_check = check_persistent(guestname, target)
                if not config_check:
                    logger.info("detach disk from guest succeed")
                    return 0
                else:
                    logger.error("check config xml failed")
                    return 1
            except libvirtError, e:
                logger.info("libvirt call failed: " + str(e))
                return 1

    elif state == libvirt.VIR_DOMAIN_RUNNING:
        try:
            domobj.detachDeviceFlags(xmlstr, int(flags))
        except libvirtError, e:
            logger.error("libvirt call failed: " + str(e))
            return 1

        disk_num2 = utils.dev_num(guestname, "disk")
        ret = check_disk(disk_num1, disk_num2)
        config_check = check_persistent(guestname, target)

        if flags == 0 or flags == 1:
            if ret == 1:
                if not config_check:
                    logger.info("detach disk from guest succeed")
                    return 0
                else:
                    logger.error("config xml also changed, it's not expected")
                    return 1
            else:
                logger.error("check current xml failed")
                return 1
        elif flags == 2:
            if ret == 1:
                if config_check:
                    logger.error("config xml not changed, it's not expected")
                    return 1
                else:
                    logger.info("detach disk from guest succeed")
                    return 0
            else:
                logger.error("check current xml failed")
                return 1
        else:
            if ret == 1 and not config_check:
                logger.info("detach disk from guest succeed")
                return 0
            else:
                logger.error("check current or config xml failed")
                return 1

    else:
        logger.error("only support domain running or shutoff")
        return 1


def attach_disk(domobj, guestname, state, xmlstr, flags, target, disk_num1,
                logger):
    """Attach a disk with xml to domain with flags"""
    logger.info("attach disk with flags: %s" % flags)

    if state == libvirt.VIR_DOMAIN_SHUTOFF:
        if flags == 1 or flags == 3:
            try:
                domobj.attachDeviceFlags(xmlstr, int(flags))
                logger.error("this should fail")
                return 1
            except libvirtError, e:
                logger.error("libvirt call failed: " + str(e))
                logger.info("live attach fail on shutoff domain is expected")
                return 0

        else:
            try:
                domobj.attachDeviceFlags(xmlstr, int(flags))
                disk_num2 = utils.dev_num(guestname, "disk")
                ret = check_disk(disk_num1, disk_num2)

                if ret == 2:
                    logger.info("attach disk to guest succeed")
                    return 0
                else:
                    logger.error("check current xml failed")
                    return 1
            except libvirtError, e:
                logger.info("libvirt call failed: " + str(e))
                return 1

    elif state == libvirt.VIR_DOMAIN_RUNNING:
        try:
            domobj.attachDeviceFlags(xmlstr, int(flags))
        except libvirtError, e:
            logger.error("libvirt call failed: " + str(e))
            return 1

        disk_num2 = utils.dev_num(guestname, "disk")
        ret = check_disk(disk_num1, disk_num2)
        config_check = check_persistent(guestname, target)

        if flags == 0 or flags == 1:

            if ret == 2:
                if not config_check:
                    logger.info("attach disk to guest succeed")
                    return 0
                else:
                    logger.error("config xml changed, it's not expected")
                    return 1
            else:
                logger.error("check current xml failed")
                return 1
        elif flags == 2:
            if ret == 1:
                if config_check:
                    logger.info("attach disk to guest succeed")
                    return 0
                else:
                    logger.error("config xml not changed, it's not expected")
                    return 1
            else:
                logger.error("check current xml failed")
                return 1

        else:
            if config_check and ret == 2:
                logger.info("attach disk to guest succeed")
                return 0
            else:
                logger.error("check current or config xml failed")
                return 1

    else:
        logger.error("please make sure domain is running or shutoff")
        return 1


def disk_hotplug(params):
    """Loop attach/detach disk through xml on domain with all supported
       flags
    """
    logger = params['logger']
    guestname = params['guestname']
    imageformat = params['imageformat']
    hddriver = params['hddriver']
    xmlstr = params['xml']
    out = 0

    imagesize = int(params.get('imagesize', 1))
    diskpath = params.get('diskpath', '/var/lib/libvirt/images/attacheddisk')

    if create_image(diskpath, imagesize, imageformat, logger):
        logger.error("fail to create a image file")
        return 1

    conn = sharedmod.libvirtobj['conn']
    domobj = conn.lookupByName(guestname)

    state = domobj.info()[0]
    logger.debug("current guest status: %s" % state)
    if not (state == libvirt.VIR_DOMAIN_SHUTOFF or
            state == libvirt.VIR_DOMAIN_RUNNING):
        logger.error("guest not in shutoff or running state")
        return 1

    if hddriver == 'virtio':
        xmlstr = xmlstr.replace('DEV', 'vdb')
        target = 'vdb'
    elif hddriver == 'ide':
        xmlstr = xmlstr.replace('DEV', 'hdb')
        target = 'hdb'
    elif hddriver == 'scsi':
        xmlstr = xmlstr.replace('DEV', 'sdb')
        target = 'sdb'

    logger.debug("disk xml:\n%s" % xmlstr)

    disk_num1 = utils.dev_num(guestname, "disk")
    logger.debug("original disk number: %s" % disk_num1)

    for i in reversed(range(4)):
        attach_ret = attach_disk(domobj, guestname, state, xmlstr, i, target,
                                 disk_num1, logger)
        time.sleep(5)
        detach_ret = detach_disk(domobj, guestname, state, xmlstr, i, target,
                                 disk_num1, logger)
        time.sleep(5)
        ret = int(attach_ret) + int(detach_ret)
        out += ret

    if out:
        return 1
    else:
        return 0

def disk_hotplug_clean(params):
    """
    Cleanup the test environment.
    """

    logger = params['logger']
    ret_flag = params.get("ret_flag")
    logger.info("The test return %s, try to cleanup...\n" % ret_flag)
    conn = sharedmod.libvirtobj['conn']
    guestname = params['guestname']
    domobj = conn.lookupByName(guestname)
    if not domobj.isActive():
        logger.info("Start the domain")
        start(params)

    return 0

