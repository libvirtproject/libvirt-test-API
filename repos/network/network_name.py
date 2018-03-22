#!/usr/bin/env python
# To test "virsh net-name" command

from libvirt import libvirtError
from xml.dom import minidom
from src import sharedmod
from utils import utils

required_params = ('networkname',)
optional_params = {}

VIRSH_NETNAME = "virsh net-name"


def check_network_exists(conn, networkname, logger):
    """ check if the network exists, may or may not be active """
    network_names = conn.listNetworks()
    network_names += conn.listDefinedNetworks()

    if networkname not in network_names:
        logger.error("%s doesn't exist" % networkname)
        return False
    else:
        return True


def check_network_bridge_name(network_obj, network_bridge_name, logger):
    """ check the network bridge name """
    netxml = network_obj.XMLDesc(0)

    doc = minidom.parseString(netxml)
    bridge_element = doc.getElementsByTagName('bridge')[0]
    bridge_name = bridge_element.attributes['name'].value
    logger.debug("bridge name from xml is %s" % bridge_name)
    if cmp(network_bridge_name, bridge_name) == 0:
        logger.debug("the bridge name is right")
        return True
    else:
        logger.error("the bridge name is not right")
        return False


def check_network_uuid(networkname, UUIDString, logger):
    """ check the output of virsh net-name """
    cmd = VIRSH_NETNAME + " " + UUIDString
    (status, ret) = utils.exec_cmd(cmd, shell=True)
    if status:
        logger.error("executing " + "\"" + VIRSH_NETNAME + ' %s' % UUIDString +
                     "\"" + " failed")
        logger.error(ret)
        return False
    else:
        networkname_virsh = str(ret[0])
        logger.debug("networkname from " + VIRSH_NETNAME + " is %s"
                     % networkname_virsh)
        logger.debug("networkname we expected is %s" % networkname)
        if networkname_virsh == networkname:
            return True
        else:
            return False


def network_name(params):
    """ get the UUIDString of a network, then call
        virsh net-name to generate the name of network,
        then check it
    """
    logger = params['logger']
    networkname = params['networkname']

    conn = sharedmod.libvirtobj['conn']

    if not check_network_exists(conn, networkname, logger):
        logger.error("need a defined network")
        return 1

    netobj = conn.networkLookupByName(networkname)

    try:
        UUIDString = netobj.UUIDString()
        bridge_name = netobj.bridgeName()

        logger.info("the UUID string of network %s is %s" %
                    (networkname, UUIDString))
        logger.info("the bridge name of network %s is %s" %
                    (networkname, bridge_name))

        if check_network_bridge_name(netobj, bridge_name, logger):
            logger.info("bridgeName test succeeded.")
            bridge_ret = True
        else:
            logger.error("bridgeName test failed.")
            bridge_ret = False
        if check_network_uuid(networkname, UUIDString, logger):
            logger.info(VIRSH_NETNAME + " " + UUIDString + " test succeeded.")
            networkname_ret = True
        else:
            logger.error(VIRSH_NETNAME + " " + UUIDString + " test failed.")
            networkname_ret = False
        if bridge_ret and networkname_ret:
            return 0
        else:
            return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    return 0
