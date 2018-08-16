#!/usr/bin/env python

from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ()
optional_params = {'ifacename': ''}

GET_MAC_CMD = "ip link show %s | sed -n '2p' | awk '{print $2}'"


def get_name_list(params):
    """return the interface list
    """
    name_list = []

    if 'ifacename' in params:
        ifacename = params['ifacename']
        name_list.append(ifacename)
    else:
        try:
            name_list = conn.listInterfaces()
        except libvirtError as e:
            logger.error("API error message: %s, error code is %s"
                         % (e.get_error_message(), e.get_error_code()))
            return 1, name_list

    logger.info("the interface list is %s" % name_list)
    return 0, name_list


def check_iface_mac(iface_name, iface_mac):
    """check the mac address from MACString
    """
    status, mac_string = utils.exec_cmd(GET_MAC_CMD % iface_name, shell=True)
    if status or len(mac_string) == 0:
        logger.error("Executing " + GET_MAC_CMD % iface_name + " failed")
        logger.error(GET_MAC_CMD % iface_name)
        return False
    else:
        mac_string = mac_string[0]
        logger.debug("mac from cmd of interface %s is %s" %
                     (iface_name, mac_string))
        if cmp(iface_mac, mac_string) == 0:
            return True
        else:
            return False


def iface_mac(params):
    """ test API MACString(), if optional option 'ifacename' is given
        test it, otherwise test all interface name from the output of
        iface-list
    """
    global logger, conn
    logger = params['logger']
    conn = sharedmod.libvirtobj['conn']

    status, name_list = get_name_list(params)

    if status:
        logger.error("Failed to get the interface list.")
        return 1

    try:
        for iface_name in name_list:
            iface_obj = conn.interfaceLookupByName(iface_name)
            iface_mac = iface_obj.MACString()
            logger.info("the mac of interface %s is %s" %
                        (iface_name, iface_mac))
            if check_iface_mac(iface_name, iface_mac):
                logger.info("get the mac successfully")
            else:
                logger.error("fail to get the mac")
                return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    return 0
