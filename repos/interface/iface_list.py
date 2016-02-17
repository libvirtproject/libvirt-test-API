#!/usr/bin/env python
# test listAllInterfaces() API

import os
import libvirt

from libvirt import libvirtError
from src import sharedmod
from utils import utils


required_params = ('flags',)
optional_params = {}

NETWORK_CONFIG = "/etc/sysconfig/network-scripts/"
IFCONFIG_DRIVER = "ifconfig %s | sed 's/[ \t].*//;/^$/d'| cut -d \":\" -f -1"


def get_inteface_list_from_ifcfg(logger):
    """
       return host interface list from ifcfg-*
    """
    ifcfg_files = []
    nic_names = []
    for f in os.listdir(NETWORK_CONFIG):
        if f.startswith("ifcfg-"):
            f_path = os.path.join(NETWORK_CONFIG, f)
            if os.path.isfile(f_path):
                ifcfg_files.append(f_path)
            else:
                logger.warn("%s is not a regular file" % f_path)
    for ifcfg_file in ifcfg_files:
        fp = open(ifcfg_file, 'r')
        fp.seek(0, 0)
        for eachLine in fp:
            if eachLine.startswith('DEVICE'):
                device_str = eachLine.rstrip()
                nic_string = device_str.split("=")[1]
                if nic_string.startswith("\""):
                    nic_names.append(nic_string[1:-1])
                else:
                    nic_names.append(nic_string)
                break
        fp.close()
    return list(set(nic_names))


def get_interface_list(option, logger):
    """
       return host interface list
    """
    nic_names = []
    status, nic_names = utils.exec_cmd(IFCONFIG_DRIVER % option, shell=True)
    if not status:
        return nic_names
    else:
        logger.error("\"" + IFCONFIG_DRIVER % option + "\"" + "error")
        logger.error(nic_names)
        return nic_names


def iface_list_output_from_ifconfig(flags, logger):
    """
       get all host interface using ifconfig command
    """
    nic_names = []
    if flags == 0:
        nic_names = get_interface_list('-a', logger)
    else:
        nic_names = get_interface_list('', logger)

    if nic_names is None:
        return False
    return nic_names


def iface_list_output_from_api(flags, logger):
    """
       get interface list using listAllInterfaces()
    """
    nic_names_api = []
    for interface in conn.listAllInterfaces(flags):
        nic_names_api.append(str(interface.name()))
    return nic_names_api


def iface_list_expect(flag, logger):
    """
       gen iface list according to flag
    """
    iface_list_ifconfig = iface_list_output_from_ifconfig(flag, logger)
    if not iface_list_ifconfig:
        return 1

    ifcfg = get_inteface_list_from_ifcfg(logger)
    logger.info("interface list from ifconfig: %s" % iface_list_ifconfig)
    logger.info("interface list from ifcfg: %s" % ifcfg)
    if flag == 0:
        return list(set(iface_list_ifconfig + ifcfg))
    if flag == 1:
        for interface in iface_list_ifconfig:
            if interface in ifcfg:
                ifcfg.remove(interface)
                logger.debug("%s is active" % interface)
        return ifcfg
    if flag == 2:
        for interface in iface_list_ifconfig:
            if interface not in ifcfg:
                iface_list_ifconfig.remove(interface)
                logger.debug("%s has not regular ifcfg file" % interface)
        return iface_list_ifconfig


def iface_list(params):
    """
       test listAllInterfaces() api
    """
    global conn
    logger = params['logger']
    flags = params['flags']
    conn = sharedmod.libvirtobj['conn']
    logger.info("The given flags is %s " % flags)
    if flags == "all":
        flag = 0
    elif flags == "inactive":
        flag = 1
    elif flags == "active":
        flag = 2
    try:
        iface_list = iface_list_output_from_api(flag, logger)
        logger.info("interface list from API: %s" % iface_list)
        iface_expect = iface_list_expect(flag, logger)
        logger.info("interfaces expected to show up: %s" % iface_expect)
        for interface in iface_list:
            if interface in iface_expect:
                logger.debug("%s :Pass" % interface)
            else:
                logger.debug("%s :Fail" % interface)
                return 1

    except libvirtError, e:
        logger.error("API error message: %s" % e.message)
        return 1

    return 0
