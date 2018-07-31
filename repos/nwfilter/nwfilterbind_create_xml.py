#!/usr/bin/env python

import os
import time

from libvirt import libvirtError
from src import sharedmod
from utils import process, utils

required_params = ('portdev', 'mac_addr')
optional_params = {'xml': 'xmls/nwfilterbind.xml',
                   'owner_name': 'test-api',
                   'owner_uuid': 'd54df46f-1ab5-4a22-8618-4560ef5fac2c'}


def check_ebtables_rule(portdev, logger):
    cmd = "ebtables -t nat -L | grep %s" % portdev
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("%s failed: %s." % (cmd, ret.stdout))
        return False
    return True


def nwfilterbind_create_xml(params):
    logger = params['logger']
    xmlstr = params['xml']

    owner_name = params.get('owner_name', 'test-api')
    owner_uuid = params.get('owner_uuid', 'd54df46f-1ab5-4a22-8618-4560ef5fac2c')
    portdev = params['portdev']
    mac_addr = params['mac_addr']

    if not utils.version_compare("libvirt-python", 4, 5, 0, logger):
        logger.info("Current libvirt-python don't support nwfilterBindingCreateXML().")
        return 0

    xmlstr = xmlstr.replace('OWNER_NAME', owner_name)
    xmlstr = xmlstr.replace('OWNER_UUID', owner_uuid)
    xmlstr = xmlstr.replace('PORTDEV', portdev)
    xmlstr = xmlstr.replace('MAC_ADDR', mac_addr)
    try:
        conn = sharedmod.libvirtobj['conn']
        logger.info("XML:\n%s" % xmlstr)

        conn.nwfilterBindingCreateXML(xmlstr)
        time.sleep(3)
        if not check_ebtables_rule(portdev, logger):
            logger.error("FAIL: check ebtables rule failed.")
            return 1
        else:
            logger.info("PASS: ebtables rule is added.")

    except libvirtError as e:
        logger.error("API error message: %s" % e.get_error_message())
        return 1

    return 0
