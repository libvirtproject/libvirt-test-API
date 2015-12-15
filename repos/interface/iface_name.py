#!/usr/bin/env python

import os
import sys
import re
import commands

required_params = ()
optional_params = {'macaddr': ''}

VIRSH_QUIET_IFACE_LIST = "virsh --quiet iface-list --all | awk '{print ""$%s""}'"
GET_MAC = "ip link show %s |sed -n '2p'| awk '{print $2}'"
VIRSH_IFACE_NAME = "virsh iface-name %s"


def get_output(command, logger):
    """execute shell command
    """
    status, ret = commands.getstatusoutput(command)
    if status:
        logger.error("executing " + "\"" + command + "\"" + " failed")
        logger.error(ret)
    return status, ret


def get_mac_list(params):
    """return mac we need to test
    """
    logger = params['logger']
    mac_list = []

    if 'macaddr' in params:
        macaddr = params['macaddr']
        mac_list.append(macaddr)
    else:
        status, ret = get_output(VIRSH_QUIET_IFACE_LIST % 3, logger)
        if not status:
            mac_list = ret.split('\n')
        else:
            return 1, mac_list

    logger.info("list of mac we are going to test: %s" % mac_list)
    return 0, mac_list


def iface_name(params):
    """ test iface_name, if optional option 'macaddr' is given
        test it, otherwise test all mac address from the output of
        iface-list
    """
    logger = params['logger']
    status, mac_list = get_mac_list(params)

    if status:
        return 1

    for mac in mac_list:
        status, interface_str = get_output(VIRSH_IFACE_NAME % mac, logger)
        if not status:
            interface_name = interface_str.rstrip()
            logger.info("the interface name generate from " +
                        VIRSH_IFACE_NAME % mac + " is: '%s'" % interface_name)
        else:
            return 1

        status, interface_mac = get_output(GET_MAC % interface_name, logger)
        logger.info("the interace '%s' has mac address: '%s'" %
                    (interface_name, interface_mac))

        if not status:
            if interface_mac == mac:
                logger.info("the mac '%s' we tested is equal to it should be '%s'" %
                            (mac, interface_mac))
            else:
                logger.error("the mac '%s' we tested is not equal to it should be '%s'" %
                             (mac, interface_mac))
                return 1

    return 0
