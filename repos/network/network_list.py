#!/usr/bin/env python
# To test "virsh net-list" command

from libvirt import libvirtError
from src import sharedmod
from utils import utils

required_params = ('flags',)
optional_params = {}

LS_NETWORK_DIR = "ls /etc/libvirt/qemu/networks/"
LS_AUTOSTART_NET = "ls /etc/libvirt/qemu/networks/autostart/"


def check_persistent_netxml(networkname):
    """
        Check if the network is persistent via checking network xml dir
        if the network is persistent, return True, or return False
    """

    (status, output) = utils.exec_cmd(LS_NETWORK_DIR, shell=True)
    network_list_dir = []
    if status:
        logger.error("Executing " + LS_NETWORK_DIR + " failed")
        logger.error(output)
        return False
    else:
        for i in range(len(output)):
            network_list_dir.append(output[i][:-4])
        del network_list_dir[0]
        logger.info("Get persistent network name list under dir: %s"
                    % network_list_dir)
        if networkname in network_list_dir:
            return True
        else:
            return False


def check_autostart_netxml(networkname):
    """
        Check if the network is autostart via checking network autostart dir
        if the network is autostart , return True, or return False.
    """

    (status, output) = utils.exec_cmd(LS_AUTOSTART_NET, shell=True)
    autostart_list_dir = []
    if status:
        logger.error("Executing " + LS_AUTOSTART_NET + " failed")
        logger.error(output)
        return False
    else:
        for i in range(len(output)):
            autostart_list_dir.append(output[i][:-4])
        logger.info("Get autostart network name list under dir: %s"
                    % autostart_list_dir)
        if networkname in autostart_list_dir:
            return True
        else:
            return False


def network_list(params):
    """ List network with flag """

    global logger
    logger = params['logger']
    conn = sharedmod.libvirtobj['conn']
    flags = params['flags']
    logger.info("The given flags is %s " % flags)
    flag = -1
    if flags == "default":
        flag = 0
    elif flags == "inactive":
        flag = 1
    elif flags == "active":
        flag = 2
    elif flags == "persistent":
        flag = 4
    elif flags == "transient":
        flag = 8
    elif flags == "autostart":
        flag = 16
    elif flags == "noautostart":
        flag = 32
    try:
        network_list_api = conn.listAllNetworks(flag)
        network_namelist_api = []
        logger.debug("Traverse the network object list %s" %
                     network_list_api)
        for network in network_list_api:
            networkname = network.name()
            logger.info("Network name: %s " % networkname)
            # Check if the network is active
            if cmp(flags, "active") == 0:
                if network.isActive():
                    logger.info("The %s network is active" % networkname)
                else:
                    logger.error("Failed ,the %s network isn't active" %
                                 networkname)
                    return 1

            # Check if the network is persistent
            if cmp(flags, "persistent") == 0:
                if network.isPersistent() and \
                        check_persistent_netxml(networkname):
                    logger.info("The %s network is persistent" % networkname)
                else:
                    logger.error("Failed ,the %s network isn't persistent" %
                                 networkname)
                    return 1

            # Check if the network is auto start
            if cmp(flags, "autostart") == 0:
                if check_autostart_netxml(networkname):
                    logger.info("The %s network is autostart" % networkname)
                else:
                    logger.error("Failed ,the %s network isn't autostart" %
                                 networkname)
                    return 1

            network_namelist_api.append(networkname)
        logger.info("The network list %s" % network_namelist_api)

    except libvirtError as e:
        logger.error("API error message: %s" % e.message)
        return 1

    return 0
