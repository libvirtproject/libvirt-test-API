#!/usr/bin/env python
import libvirt
from libvirt import libvirtError
from utils import utils

required_params = ()
optional_params = {'conn': ''}

NODE_ONLINE = '/sys/devices/system/node/online'


def getnodemem(path):
    return open(path).read().splitlines()[1].split()[3]


def virtgetmem(a):
    return a[0].getCellsFreeMemory(a[1], a[1] + 1)[0] / 1024


def connection_getCellsFreeMemory(params):
    """
       test API for getCellsFreeMemory in class virConnect
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

        logger.info("get connection cells free memory")
        for n in range(len(node_tuple)):
            if not node_tuple[n]:
                continue

            D = utils.get_standard_deviation(getnodemem, virtgetmem,
                                             '/sys/devices/system/node/node%d/meminfo' % n, [conn, n])
            logger.info("Standard Deviation for node %d is %d" % (n, D))

            """ expectations 177 is a average collected in a x86_64 low load machine"""
            if D > 177 * 5:
                fail = 1
                logger.info("FAIL: Standard Deviation is too big \
                             (biger than %d) for node %d" % (177 * 5, n))

    except libvirtError as e:
        logger.error("API error message: %s" % e.message)
        fail = 1
    return fail
