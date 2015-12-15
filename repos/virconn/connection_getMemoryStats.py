#!/usr/bin/env python
import libvirt
from libvirt import libvirtError
from utils import utils

required_params = ()
optional_params = {'conn': ''}

NODE_ONLINE = '/sys/devices/system/node/online'
MEMINFO = '/proc/meminfo'


def getsysmem(a):
    return open(a[0]).read().splitlines()[a[1]].split()[a[2]]


def virtgetmem(a):
    return a[0].getMemoryStats(a[1])[a[2]]


def connection_getMemoryStats(params):
    """
       test API for getMemoryStats in class virConnect
    """
    logger = params['logger']
    fail = 0

    nodeset = utils.file_read(NODE_ONLINE)
    logger.info("host exist node is %s" % nodeset)

    node_tuple = utils.param_to_tuple_nolength(nodeset)
    if not node_tuple:
        logger.info("error in function param_to_tuple_nolength")
        return 1

    try:
        conn = libvirt.open(params['conn'])

        logger.info("get connection cells memory status")
        for n in range(len(node_tuple)):
            if not node_tuple[n]:
                continue

            D = utils.get_standard_deviation(getsysmem, virtgetmem,
                                             ['/sys/devices/system/node/node%d/meminfo' % n, 1, 3], [conn, n, 'free'])
            logger.info("Standard Deviation for free memory in node %d is %d" % (n, D))

            """ expectations 177 is a average collected in a x86_64 low load machine"""
            if D > 177 * 5:
                fail = 1
                logger.info("FAIL: Standard Deviation is too big \
                             (biger than %d) for node %d free memory" % (177 * 5, n))

            a1 = ['/sys/devices/system/node/node%d/meminfo' % n, 0, 3]
            a2 = [conn, n, 'total']
            if long(getsysmem(a1)) != long(virtgetmem(a2)):
                fail = 1
                logger.info("FAIL: Total memory in node %d is not right" % n)

        D = utils.get_standard_deviation(getsysmem, virtgetmem,
                                         [MEMINFO, 3, 1], [conn, -1, 'buffers'])
        logger.info("Standard Deviation for host buffers is %d" % D)

        """ expectations 30 is a average collected in a x86_64 low load machine"""
        if D > 30 * 5:
            fail = 1
            logger.info("FAIL: Standard Deviation is too big \
                         (biger than %d) for host buffers" % 30 * 5)

        D = utils.get_standard_deviation(getsysmem, virtgetmem,
                                         [MEMINFO, 4, 1], [conn, -1, 'cached'])
        logger.info("Standard Deviation for host cached is %d" % D)

        """ expectations 32 is a average collected in a x86_64 low load machine"""
        if D > 32 * 5:
            fail = 1
            logger.info("FAIL: Standard Deviation is too big \
                         (biger than %d) for host cached" % 32 * 5)

        D = utils.get_standard_deviation(getsysmem, virtgetmem,
                                         [MEMINFO, 1, 1], [conn, -1, 'free'])
        logger.info("Standard Deviation for host free memory is %d" % D)

        """ expectations 177 is a average collected in a x86_64 low load machine"""
        if D > 177 * 5:
            fail = 1
            logger.info("FAIL: Standard Deviation is too big \
                         (biger than %d) for host free memory" % 177 * 5)

        if long(getsysmem([MEMINFO, 0, 1])) != long(virtgetmem([conn, -1, 'total'])):
            fail = 1
            logger.info("FAIL: Total memory for host is not right" % n)

    except libvirtError as e:
        logger.error("API error message: %s" % e.message)
        fail = 1
    return fail
