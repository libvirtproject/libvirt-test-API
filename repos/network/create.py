#!/usr/bin/evn python
# Create a network

import re

from libvirt import libvirtError

from src import sharedmod

required_params = ('networkname',
                   'bridgename',
                   'bridgeip',
                   'bridgenetmask',
                   'netstart',
                   'netend',
                   'netmode',)
optional_params = {'xml': 'xmls/network.xml',
                   'netip6addr': '2001:db8:ca2:98::1',
                   'netip6prefix': '64',
                   'netip6start': '2001:db8:ca2:98::11',
                   'netip6end': '2001:db8:ca2:98::ff',
                   }


def check_network_status(*args):
    """Check current network status, it will return True if
       current network is inactive, otherwise, return False
    """
    (networkname, conn, logger) = args

    net_list = conn.listNetworks()
    logger.debug("current active network list:")
    logger.debug(net_list)
    if networkname not in net_list:
        return True
    else:
        return False


def create(params):
    """Create a network from xml"""
    logger = params['logger']
    networkname = params['networkname']
    netmode = params['netmode']
    xmlstr = params['xml']

    conn = sharedmod.libvirtobj['conn']

    if not check_network_status(networkname, conn, logger):
        logger.error("the %s network is running" % networkname)
        return 1

    if netmode == 'isolate':
        xmlstr = re.sub('<forward.*\n', '', xmlstr)

    logger.debug("%s network xml:\n%s" % (networkname, xmlstr))

    net_num1 = conn.numOfNetworks()
    logger.info("original network active number: %s" % net_num1)

    try:
        conn.networkCreateXML(xmlstr)
        net_num2 = conn.numOfNetworks()
        if not check_network_status(networkname, conn, logger) and \
                net_num2 > net_num1:
            logger.info("current network active number: %s\n" % net_num2)
        else:
            logger.error("the %s network is inactive" % networkname)
            logger.error("fail to create network from :\n%s" % xmlstr)
            return 1
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        logger.error("create a network from xml: \n%s" % xmlstr)
        return 1

    return 0
