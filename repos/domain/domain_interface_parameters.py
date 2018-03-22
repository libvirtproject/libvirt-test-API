#!/usr/bin/env python
# To test domain's interfaceParameters API

import re
import libvirt

from libvirt import libvirtError
from src import sharedmod
from src.exception import TestError
from utils import process

required_params = ('guestname', 'mac')
optional_params = {}


def find_rate(name, src):
    """Get formatted rate info from tc output"""
    formats = {
        'nbit': r' %s (\d+[M,K]?)bit' % name,
        'nbyte': r' %s (\d+[M,K]?)b' % name,
        'ebit': r' %s 1e\+(\d+[M,K]?)bit' % name,
        'ebyte': r' %s 1e\+(\d+[M,K]?)b' % name,
    }

    found = False
    for i in formats:
        raw = re.findall(formats[i], src)
        if raw and len(raw) == 1:
            raw = raw[0]
            found = i
            break

    mul, div = 1, 1
    if found:
        if raw[-1] == 'M':
            raw = raw[:-1]
            mul = 1000000
        if raw[-1] == 'K':
            raw = raw[:-1]
            mul = 1000

        if found in ['nbit', 'ebit']:
            div = 8

        if found in ['nbit', 'nbyte']:
            return int(raw)*mul/div

        if found in ['ebyte', 'ebit']:
            return pow(10, int(raw))*mul/div

    else:
        # No class, no filter, no parameter, return default value 0
        return 0


def domain_interface_parameters(params):
    """ check the output of interfaceParameters
    """
    logger = params['logger']
    guestname = params.get('guestname')
    mac = params.get('mac')
    test_flag_set = [
        # Return values with thoes flags will be verified with tc output
        libvirt.VIR_DOMAIN_AFFECT_CURRENT,
        libvirt.VIR_DOMAIN_AFFECT_LIVE,
        libvirt.VIR_DOMAIN_AFFECT_CURRENT | libvirt.VIR_TYPED_PARAM_STRING_OKAY,
        libvirt.VIR_DOMAIN_AFFECT_LIVE | libvirt.VIR_TYPED_PARAM_STRING_OKAY,
    ]
    config_flag_set = [
        # Return values with thoes flags will not be verified
        libvirt.VIR_DOMAIN_AFFECT_CONFIG,
        libvirt.VIR_DOMAIN_AFFECT_CONFIG | libvirt.VIR_TYPED_PARAM_STRING_OKAY,
    ]
    bad_flag = [
        # Thoes illegal flags should cause Exception
        libvirt.VIR_DOMAIN_AFFECT_CONFIG | libvirt.VIR_TYPED_PARAM_STRING_OKAY
        | libvirt.VIR_DOMAIN_AFFECT_LIVE,
        -1,
    ]

    logger.info("the name of guest is %s" % guestname)

    conn = sharedmod.libvirtobj['conn']

    cmd = "virsh domiflist %s" % guestname
    ret = process.run(cmd, shell=True, ignore_status=True)
    dev_name = re.findall(r'\n([a-zA-Z0-9]+)\s.*%s' % mac, ret.stdout)
    if not dev_name or len(dev_name) != 1:
        logger.error("Failed to find interface with mac address: %s "
                     "maybe the guest is not started" % mac)
        return 1

    dev_name = dev_name[0]
    logger.info("Interface %s is connected to virtual net %s" % (mac, dev_name))

    cmd = "tc class show dev %s" % dev_name
    inbound_tc = process.system_output(cmd, shell=True, ignore_status=True)
    cmd = "tc filter show dev %s parent ffff:" % dev_name
    outbound_tc = process.system_output(cmd, shell=True, ignore_status=True)

    inbound = {
        'average': find_rate('rate', inbound_tc)/1000,
        'peak': find_rate('ceil', inbound_tc)/1000,
        'burst': find_rate('burst', inbound_tc)/1000,
    }
    outbound = {
        'average': find_rate('rate', outbound_tc)/1000,
        'peak': find_rate('peakrate', outbound_tc)/1000,
        'burst': find_rate('burst', outbound_tc)/1000,
    }

    logger.info("tc gives the params: inbound: %s, outbound:%s"
                % (str(inbound), str(outbound)))

    def check_value(api):
        """Check if value of api is the same as tc output
           or the are using default value.
        """
        if int(api['outbound.average']) != outbound['average']:
            return False
        if int(api['outbound.burst']) != outbound['burst']:
            if int(api['outbound.burst']) != 0:
                return False
            if outbound['burst'] != int(api['outbound.average']):
                return False
        # outbound.peak ignored
        if int(api['inbound.average']) != inbound['average']:
            return False
        if int(api['inbound.peak']) != inbound['peak']:
            if int(api['inbound.peak']) != 0:
                return False
            if inbound['peak'] != int(api['inbound.average']):
                # When inbound.burst is not set, tc default value equals to average
                return False
        if int(api['inbound.burst']) != inbound['burst']:
            if int(api['inbound.burst']) != 0:
                return False
            if inbound['burst'] != 1:
                return False
        return True

    try:
        domobj = conn.lookupByName(guestname)

        logger.info("Calling interfaceParameters with multiple flags")
        for flag in test_flag_set:
            interface_param = domobj.interfaceParameters(mac, flag)
            logger.info("Flag = %d" % flag)
            logger.info("Got parameters %s" % str(interface_param))
            if check_value(interface_param):
                logger.info("Same as tc")
            else:
                logger.error("Diffrent from tc!")
                return 1

        logger.info("Try to read config:")
        for flag in config_flag_set:
            interface_param = domobj.interfaceParameters(mac, flag)
            logger.info("Flag = %d" % flag)
            logger.info("Got configtion %s" % str(interface_param))

        logger.info("Calling interfaceParameters with bad flags")
        success = True
        for flag in bad_flag:
            if not success:
                logger.error('No exception raised.')
                return 1
            success = False
            try:
                interface_param = domobj.interfaceParameters(mac, flag)
            except libvirtError as e:
                success = True
                logger.info('Got exception as expected')

    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    return 0
