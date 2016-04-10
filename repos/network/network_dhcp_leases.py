#!/usr/bin/env python
# test DHCPLeases() API for libvirt

import os
import json

from libvirt import libvirtError
from utils import utils
from src import sharedmod

required_params = ('networkname',)
optional_params = {'macaddr': ''}

LEASE_FILE = "/var/lib/libvirt/dnsmasq/"


def check_ip(ipaddr, logger):
    """
       return a string according to ip address type, return 'ipv4' for ipv4,
       return 'ipv6' for ipv6, return False for others
    """
    addr4 = ipaddr.strip().split('.')
    addr6 = ipaddr.strip().split(':')
    if len(addr4) == 4:
        iptype = "ipv4"
    elif len(addr6) == 6:
        iptype = "ipv6"
    else:
        return False
    return iptype


def get_network_type(ipaddr, logger):
    """
       return 0 or 1 for ipv4/ipv6, this function will be used in
       check_ipv4_values()/check_ipv6_values()
    """
    if check_ip(ipaddr, logger) == "ipv4":
        return 0
    elif check_ip(ipaddr, logger) == "ipv6":
        return 1


def get_bridge_name(network, logger):
    """
       get bridge name under specified network from specified network conf
    """
    CONF_NETWORK = LEASE_FILE + network + ".conf"
    GREP_BRIDGE = "grep \"^interface=\" %s | awk -F\"=\" '{print $2}'"
    status, output = utils.exec_cmd(GREP_BRIDGE % CONF_NETWORK, shell=True)
    if not status:
        pass
    else:
        logger.error("\"" + GREP_BRIDGE + "\"" + "error")
        logger.error(output)
        return False

    return output[0]


def get_ip_prefix(network, iptype, logger):
    """
       get ip prefix according to IP type
    """
    br = get_bridge_name(network, logger)
    PREFIX = "ip -4 -o ad show %s | awk '{print $4}'|awk -F\"/\" '{print $2}'"
    PREFIX_6 = "ip -6 -o ad show %s|awk '{print $4}'|awk -F\"/\" '{print $2}'"
    if iptype == "ipv4":
        status, output = utils.exec_cmd(PREFIX % br, shell=True)
    elif iptype == "ipv6":
        status, output = utils.exec_cmd(PREFIX_6 % br, shell=True)
    if not status:
        pass
    else:
        if iptype == "ipv4":
            logger.error("\"" + PREFIX + "\"" + "error")
        if iptype == "ipv6":
            logger.error("\"" + PREFIX_6 + "\"" + "error")
        logger.error(output)
        return False
    return output[0]


def get_info_from_dnsmasq(status_file, logger):
    """
       generate info from bridge's status file
    """
    f = open(status_file, 'r')
    output = json.load(f)

    return output



def compare_values(op1, op2, network, iptype, logger):
    """
       check all printed values from API
    """
    dnsmasq = op1
    api = op2
    temp = int(api['expirytime'])
    api['expirytime'] = temp

    for j in range(0, len(dnsmasq)):
        if dnsmasq[j]['expiry-time'] == api['expirytime']:
            if dnsmasq[j]['mac-address'] == api['mac']:
                if dnsmasq[j]['ip-address'] == api['ipaddr']:
                    logger.info("PASS: mac: %s" % api['mac'])
                    logger.info("PASS: ip: %s" % api['ipaddr'])
                    logger.info("PASS: expiry-time: %s" % api['expirytime'])
                else:
                    logger.error("FAIL: ip: %s" % api['ipaddr'])
                    return False
                break
            else:
                if j == len(dnsmasq) - 1:
                    logger.error("Last loop %d, FAIL: mac: %s" % (j, api['mac']))
                    return False

        else:
            if j == len(dnsmasq) - 1:
                logger.error("Last loop %d, FAIL: expirttime: %s" % (j, api['expirttime']))
                return False

    if not api['type'] == get_network_type(api['ipaddr'], logger):
        logger.error("FAIL: type: %s" % api['type'])
        return False
    else:
        logger.info("PASS: type: %s" % api['type'])

    if not api['prefix'] == int(get_ip_prefix(network, iptype, logger)):
        logger.error("FAIL: prefix: %s" % api['prefix'])
        return False
    else:
        logger.info("PASS: prefix: %s" % api['prefix'])

    if iptype == "ipv4":
        if not api['iaid'] is None:
            logger.error("FAIL: iaid: %s" % api['iaid'])
            return False
        else:
            logger.debug("PASS: unsupported iaid: %s in IPv4" % api['iaid'])

    return True


def check_values(op1, op2, networkname, logger):
    """
       check each line accorting to ip type, if ipv4 go to check_ipv4_values
       if ipv6, go to check_ipv6_values.
    """
    dnsmasq = op1
    api = op2

    for i in range(0, len(api)):
        if check_ip(api[i]['ipaddr'], logger) == "ipv4":
            if not compare_values(dnsmasq, api[i], networkname, "ipv4", logger):
                return False
        elif check_ip(api[i]['ipaddr'], logger) == "ipv6":
            if not compare_values(dnsmasq, api[i], networkname, "ipv6", logger):
                return False
        else:
            logger.error("invalid list element for ipv4 and ipv6")
            return False
    return True


def network_dhcp_leases(params):
    """
       test API for DHCPLeases in class virNetwork
    """
    global LEASE_FILE_DNSMASQ
    logger = params['logger']
    networkname = params['networkname']

    bridgename = get_bridge_name(networkname, logger)

    LEASE_FILE_DNSMASQ = "/var/lib/libvirt/dnsmasq/" + bridgename + ".status"
    logger.info("Bridge name is %s" % (bridgename))
    mac_value = params.get('macaddr', None)
    conn = sharedmod.libvirtobj['conn']
    logger.info("The given mac is %s" % (mac_value))

    if not os.path.exists(LEASE_FILE_DNSMASQ):
        logger.error("%s file is not exist." % LEASE_FILE_DNSMASQ)
        return 1

    file_len = os.stat(LEASE_FILE_DNSMASQ).st_size
    if file_len == 0:
        dhcp_lease_dns = []
    else:
        dhcp_lease_dns = get_info_from_dnsmasq(LEASE_FILE_DNSMASQ, logger)

    logger.info("From dnsmasq: %s" % (dhcp_lease_dns))

    netobj = conn.networkLookupByName(networkname)

    try:
        dhcp_lease_api = netobj.DHCPLeases(mac_value, 0)
        logger.info("From API: %s" % (dhcp_lease_api))

        if not check_values(dhcp_lease_dns, dhcp_lease_api, networkname, logger):
            return 1

    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
