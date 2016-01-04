#!/usr/bin/env python
# To test domain's interfaceAddresses API

import commands

import libvirt
from libvirt import libvirtError
import re
import socket

from src import sharedmod
from utils import utils
from src.exception import TestError

required_params = ('guestname',)
optional_params = {}


def check_loop_valid(addr):
    """Check if a loop interface's address is valid"""
    if addr['prefix'] == 128 and addr['addr'] == '::1':
        return True
    if addr['prefix'] == 8 and re.match(r'^127(.\d{1,3}){3}$', addr['addr']):
        return True
    return False


def domain_interface_address(params):
    """ check the output of interfaceAddresses
    """
    logger = params['logger']
    guestname = params.get('guestname')

    logger.info("the name of guest is %s" % guestname)

    conn = sharedmod.libvirtobj['conn']

    try:
        domobj = conn.lookupByName(guestname)

        logger.info("checking interfaces connected to virtual networks...")
        interface_dict_lease = domobj.interfaceAddresses(
            libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE, 0)
        interface_dict = domobj.interfaceAddresses(
            libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT, 0)

    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    if len(interface_dict_lease) == 0:
        logger.error('Guest have no interface?')
        return 1

    if len(interface_dict) < len(interface_dict_lease):
        logger.error("Guest agent not running or wrongly configured!")
        return 1

    guest_address, guest_lease_address = [], []

    try:
        # Verify addresses in interface_dict_lease
        try:
            logger.info('Guest have %d interfaces connected to virtual network:'
                        % len(interface_dict_lease))
            for interface in interface_dict_lease:
                logger.info(interface)
                hwaddr = interface_dict_lease[interface]['hwaddr']
                if not utils.check_mac_valid(hwaddr):
                    logger.error("Invalid mac address: %s" % hwaddr)
                    raise TestError()

                host_address = utils.mac_to_ips(hwaddr, 60)
                logger.info("Guest have ip addresses: %s" % str(host_address))

                for addr in interface_dict_lease[interface]['addrs']:
                    if not utils.check_address_valid(addr):
                        logger.error("Invalid address struct %s" % str(addr))
                        raise TestError()

                    if addr['type'] != libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE:
                        logger.error("Type VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT"
                                     "address returned where only"
                                     "type VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE"
                                     "address is acceptable")
                        raise TestError()

                    if not addr['addr'] in host_address:
                        logger.error("Guest has IP %s which can't be seen by host!" % (addr['addr']))
                        raise TestError()

                    guest_lease_address.append(addr['addr'])

                for ip in host_address:
                    if ip not in guest_lease_address:
                        logger.error("Guest don't have IP %s which can be seen by host!" % ip)
                        raise TestError()

        except TestError, e:
            logger.error("Invalid data: %s" % str(interface_dict_lease))
            return 1

        # Verify addresses in interface_dict
        try:
            logger.info('Guest agent reported %d interfaces' % len(interface_dict))
            have_loop, loop_have_address = False, False
            for interface in interface_dict:
                logger.info(interface)
                hwaddr = interface_dict[interface]['hwaddr']
                if not utils.check_mac_valid(hwaddr):
                    logger.error("Invalid mac address: %s" % hwaddr)
                    raise TestError()
                if hwaddr == '00:00:00:00:00:00':
                    if not have_loop:
                        have_loop = True
                    else:
                        logger.error("Multiple loop founded!")
                        raise TestError()

                    for addr in interface_dict[interface]['addrs']:
                        loop_have_address = True
                        if check_loop_valid(addr):
                            continue
                        else:
                            logger.error("Invalid loop interface!")
                            raise TestError()
                    continue

                for addr in interface_dict[interface]['addrs']:
                    if not utils.check_address_valid(addr):
                        logger.error("Invalid address struct %s" % str(addr))
                        raise TestError()
                    if addr['type'] == libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE:
                        guest_address.append(addr['addr'])

            if not loop_have_address or not have_loop:
                logger.error("Loop interface not found!")
                raise TestError()

        except TestError, e:
            logger.error("Invalid data: %s" % str(interface_dict))
            return 1

        diff_address = list(set(guest_lease_address).difference(set(guest_address)))
        if len(diff_address) > 0:
            logger.error("Guest agent faild to discovery following IPs:")
            logger.error(str(diff_address))
            return 1

    except KeyError as e:
        logger.error("Return value of interfaceAddresses is incomplete"
                     "lack of attribute %s" % e.message)
        return 1

    return 0
