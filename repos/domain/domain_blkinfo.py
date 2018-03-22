#!/usr/bin/env python
# To test domain's blockkinfo API

import re

import libvirt
from libvirt import libvirtError
from utils.utils import version_compare
from src import sharedmod
from utils import process

required_params = ('guestname', 'blockdev',)
optional_params = {}


def get_output(command, logger):
    """execute shell command
    """
    ret = process.run(command, shell=True, ignore_status=True)
    logger.debug("cmd: %s" % command)
    logger.debug("ret: %s" % ret)
    if ret.exit_status:
        logger.error("executing " + "\"" + command + "\"" + " failed")
        logger.error(ret.stdout)
    return ret.exit_status, ret.stdout


def check_domain_exists(conn, guestname, logger):
    """ check if the domain exists, may or may not be active """
    guest_names = []
    ids = conn.listDomainsID()
    for domain_id in ids:
        obj = conn.lookupByID(domain_id)
        guest_names.append(obj.name())

    guest_names += conn.listDefinedDomains()

    if guestname not in guest_names:
        logger.error("%s doesn't exist" % guestname)
        return False
    else:
        return True


def check_guest_status(domobj):
    """Check guest current status"""
    state = domobj.info()[0]
    if state == libvirt.VIR_DOMAIN_SHUTOFF or \
            state == libvirt.VIR_DOMAIN_SHUTDOWN:
        # add check function
        return False
    else:
        return True


def check_block_data(blockdev, blkdata, logger):
    get_physical = "ls -l %s | awk '{print $5}'"
    qemu_img_check_re = r"(\d+)/(\d+) = \d+.\d+% allocated, (\d+.\d+)% fragmented,"

    if version_compare("qemu-kvm-rhev", 2, 10, 0, logger):
        qemu_img_format = "qemu-img info -U %s |grep format |awk -F': ' '{print $2}'"
        qemu_img_cluster_size = "qemu-img info -U %s |grep cluster_size |awk -F': ' '{print $2}'"
        qemu_img_check = "qemu-img check -U %s"
        get_capacity = "qemu-img info -U %s | grep 'virtual size' | awk '{print $4}' | sed 's/(//g'"
    else:
        qemu_img_format = "qemu-img info %s |grep format |awk -F': ' '{print $2}'"
        qemu_img_cluster_size = "qemu-img info %s |grep cluster_size |awk -F': ' '{print $2}'"
        qemu_img_check = "qemu-img check %s"
        get_capacity = "qemu-img info %s | grep 'virtual size' | awk '{print $4}' | sed 's/(//g'"

    """ check data about capacity,allocation,physical """
    status, apparent_size = get_output(get_capacity % blockdev, logger)
    if not status:
        if apparent_size == str(blkdata[0]):
            logger.info("the capacity of '%s' is %s, checking succeeded"
                        % (blockdev, apparent_size))
        else:
            logger.error("apparent-size from 'qemu-img info' is %s" % apparent_size)
            logger.error("but from 'domain blockinfo' is %d, checking failed"
                         % blkdata[0])
            return 1
    else:
        return 1

    # Add for test
    cmd_str = "du --apparent-size --block-size=1 %s | awk '{print $1}'" % blockdev
    get_output(cmd_str, logger)
    cmd_str = "du --block-size=1 %s | awk '{print $1}'" % blockdev
    get_output(cmd_str, logger)
    if version_compare("libvirt-python", 3, 8, 0, logger):
        cmd_str = "qemu-img info -U --output=json %s | grep 'actual-size' | awk '{print $2}' | sed 's/,//g'" % blockdev
    else:
        cmd_str = "qemu-img info --output=json %s | grep 'actual-size' | awk '{print $2}' | sed 's/,//g'" % blockdev
    get_output(cmd_str, logger)
    # End for test

    if version_compare("libvirt", 2, 5, 0, logger):
        status, block_size_b = get_output(get_physical % blockdev, logger)
    else:
        cmd = "du --block-size=1 %s | awk '{print $1}'" % blockdev
        status, block_size_b = get_output(cmd, logger)
    format_status, img_format = get_output(qemu_img_format % blockdev, logger)

    if not status and not format_status:
        # Temporarily, we only test the default case, assuming
        # Allocation value is equal to Physical value
        logger.info("the block size of '%s' is %s"
                    % (blockdev, block_size_b))
        if img_format.strip() == 'qcow2' and int(block_size_b) == blkdata[2]:
            logger.info("Physical value's checking succeeded")
            status, cluster_size = get_output(qemu_img_cluster_size % blockdev, logger)
            status, alloc_info = get_output(qemu_img_check % blockdev, logger)
            (allocated, total, fragment_rate) = re.findall(qemu_img_check_re, alloc_info)[0]
            fragment_rate = float(fragment_rate)/100
            alloc_size = int(allocated) * int(cluster_size)
            total_size = int(total) * int(cluster_size)
            logger.info("Allocation size is %d." % alloc_size)
            logger.info("Got size %d." % blkdata[1])
            if abs(blkdata[1] / total_size - alloc_size / total_size) < fragment_rate:
                logger.info("Allocation check for qcow2 sucessed.")
            else:
                logger.error("Allocation check for qcow2 sucessed.")
                logger.error("Expect a number near %d, got: %d"
                             % (alloc_size, blkdata[1]))
                return 1


        elif block_size_b == blkdata[1] and int(block_size_b) == blkdata[2]:
            logger.info("Allocation and Physical value's checking succeeded")
        else:
            logger.error("the block size from 'qemu-img info' is %s" % block_size_b)
            logger.error("the Allocation value is %d, Physical value is %d"
                         % (blkdata[1], blkdata[2]))
            logger.error("checking failed")
            return 1

    return 0


def domain_blkinfo(params):
    """ using du command to check the data
        in the output of API blockinfo
    """
    logger = params['logger']
    guestname = params.get('guestname')
    blockdev = params.get('blockdev')

    logger.info("the name of guest is %s" % guestname)
    logger.info("the block device is %s" % blockdev)

    conn = sharedmod.libvirtobj['conn']

    if not check_domain_exists(conn, guestname, logger):
        logger.error("need a defined guest")
        return 1

    domobj = conn.lookupByName(guestname)

    if not check_guest_status(domobj):
        logger.error("guest is not started.")
        return 1

    try:
        logger.info("the output of domain blockinfo is:")
        block_info = domobj.blockInfo(blockdev, 0)
        logger.info("Capacity  : %d " % block_info[0])
        logger.info("Allocation: %d " % block_info[1])
        logger.info("Physical  : %d " % block_info[2])

    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    if check_block_data(blockdev, block_info, logger):
        logger.error("checking domain blockinfo data FAILED")
        return 1
    else:
        logger.info("checking domain blockinfo data SUCCEEDED")

    return 0
