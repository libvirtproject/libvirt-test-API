#!/usr/bin/env python
# To test domain's blockkinfo API

import commands

import libvirt
from libvirt import libvirtError

from src import sharedmod

GET_CAPACITY = "du -b %s | awk '{print $1}'"
GET_PHYSICAL_K = " du -B K %s | awk '{print $1}'"

required_params = ('guestname', 'blockdev',)
optional_params = {}


def get_output(command, logger):
    """execute shell command
    """
    status, ret = commands.getstatusoutput(command)
    if status:
        logger.error("executing " + "\"" + command + "\"" + " failed")
        logger.error(ret)
    return status, ret


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
    """ check data about capacity,allocation,physical """
    status, apparent_size = get_output(GET_CAPACITY % blockdev, logger)
    if not status:
        if apparent_size == str(blkdata[0]):
            logger.info("the capacity of '%s' is %s, checking succeeded"
                        % (blockdev, apparent_size))
        else:
            logger.error("apparent-size from 'du' is %s" % apparent_size)
            logger.error("but from 'domain blockinfo' is %d, checking failed"
                         % blkdata[0])
            return 1
    else:
        return 1

    status, block_size_k = get_output(GET_PHYSICAL_K % blockdev, logger)
    if not status:
        block_size_b = int(block_size_k[:-1]) * 1024
        # Temporarily, we only test the default case, assuming
        # Allocation value is equal to Physical value
        if block_size_b == blkdata[1] and block_size_b == blkdata[2]:
            logger.info("the block size of '%s' is %s"
                        % (blockdev, block_size_b))
            logger.info("Allocation and Physical value's checking succeeded")
        else:
            logger.error("the block size from 'du' is %d" % block_size_b)
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

    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    if check_block_data(blockdev, block_info, logger):
        logger.error("checking domain blockinfo data FAILED")
        return 1
    else:
        logger.info("checking domain blockinfo data SUCCEEDED")

    return 0
