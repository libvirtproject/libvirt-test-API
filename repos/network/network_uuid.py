#!/usr/bin/env python
# To test "virsh net-uuid" command and related APIs
# To test 2 APIs in this case:
#      networkLookupByUUIDString
#      networkLookupByUUID

import binascii

from libvirt import libvirtError
from xml.dom import minidom
from src import sharedmod
from utils import process

required_params = ('networkname',)
optional_params = {}

VIRSH_NETUUID = "virsh net-uuid"
NWPATH = "/etc/libvirt/qemu/networks/"


def check_network_exists(conn, networkname, logger):
    """ check if the network exists, may or may not be active """
    network_names = conn.listNetworks()
    network_names += conn.listDefinedNetworks()

    if networkname not in network_names:
        logger.error("%s doesn't exist" % networkname)
        return False
    else:
        return True


def check_network_uuid(networkname, UUIDString, logger):
    """ check UUID String of a network """
    ret = process.run(VIRSH_NETUUID + ' %s' % networkname, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("executing " + "\"" + VIRSH_NETUUID + ' %s' % networkname +
                     "\"" + " failed")
        logger.error(ret.stdout)
        return False
    else:
        UUIDString_virsh = ret.stdout
        logger.debug("UUIDString from API is %s" % UUIDString)
        logger.debug("UUIDString from " + "\"" + VIRSH_NETUUID + "\"" " is %s"
                     % UUIDString_virsh)
        if UUIDString_virsh == UUIDString:
            return True
        else:
            return False


def checking_uuid(logger, nwname, nwuuid):
    """ compare two UUIDs, one is from API, another is from network XML"""
    global NWPATH
    NWPATH = NWPATH + nwname + ".xml"
    xml = minidom.parse(NWPATH)
    network = xml.getElementsByTagName('network')[0]
    uuid = network.getElementsByTagName('uuid')[0].childNodes[0].data
    if uuid == nwuuid:
        return True
    else:
        return False


def network_uuid(params):
    """ 1.call appropriate API to generate the UUIDStirng
          of a network , then compared to the output of command
          virsh net-uuid
        2.check below 2 new APIs:
           networkLookupByUUIDString
           networkLookupByUUID
    """
    global NWPATH
    logger = params['logger']
    networkname = params['networkname']

    conn = sharedmod.libvirtobj['conn']

    if not check_network_exists(conn, networkname, logger):
        logger.error("need a defined network")
        return 1

    netobj = conn.networkLookupByName(networkname)

    try:
        UUIDString = netobj.UUIDString()

        # For a transient network, set another path
        if not netobj.isPersistent() == 1:
            NWPATH = "/var/run/libvirt/network/"

        logger.info("the UUID string of network \"%s\" is \"%s\""
                    % (networkname, UUIDString))
        #allowing '-' and ' ' anywhere between character pairs, just
        #check one of them.
        UUIDString1 = UUIDString.replace("-", " ")
        network1 = conn.networkLookupByUUIDString(UUIDString1)
        nw_name1 = network1.name()
        logger.debug("The given UUID is \"%s\", the network is \"%s\" using\
 networkLookupByUUIDString" % (UUIDString1, nw_name1))

        UUIDString2 = UUIDString.replace("-", "")
        UUID_ascii = binascii.a2b_hex(UUIDString2)
        network2 = conn.networkLookupByUUID(UUID_ascii)
        nw_name2 = network2.name()
        logger.debug("The given UUID is \"%s\", the network is \"%s\" using \
networkLookupByUUID" % (UUIDString2, nw_name2))

        if nw_name1 == nw_name2 and checking_uuid(logger, nw_name1, UUIDString):
            logger.info("Successed to get network name \"%s\" using \"%s\""
                        % (nw_name1, UUIDString))

        if check_network_uuid(networkname, UUIDString, logger):
            logger.info(VIRSH_NETUUID + " test succeeded.")
            return 0
        else:
            logger.error(VIRSH_NETUUID + " test failed.")
            return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    return 0
