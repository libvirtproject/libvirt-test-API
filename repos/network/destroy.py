#!/usr/bin/evn python
# Destroy a network

from libvirt import libvirtError
from src import sharedmod

required_params = ('networkname',)
optional_params = {}


def check_network_status(*args):
    """Check current network status, it will return True if
       current network is active, otherwise, return False
    """
    (networkname, conn, logger) = args

    net_list = conn.listNetworks()
    logger.debug("current active network list:")
    logger.debug(net_list)
    if networkname in net_list:
        return True
    else:
        return False


def destroy(params):
    """destroy network"""
    logger = params['logger']
    networkname = params['networkname']

    conn = sharedmod.libvirtobj['conn']

    if not check_network_status(networkname, conn, logger):
        logger.error("the %s network is inactive" % networkname)
        return 1

    netobj = conn.networkLookupByName(networkname)
    net_num1 = conn.numOfNetworks()
    logger.info("original network active number: %s" % net_num1)

    try:
        netobj.destroy()
        net_num2 = conn.numOfNetworks()
        if not check_network_status(networkname, conn, logger) and \
                net_num1 > net_num2:
            logger.info("current network active number: %s\n" % net_num2)
            logger.info("destroy %s network successful" % networkname)
        else:
            logger.error("the %s network is still running" % networkname)
            return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("fail to destroy %s network" % networkname)
        return 1

    return 0
