#!/usr/bin/env python
# Test detachDeviceAlias() API

import libvirt
import time

from libvirt import libvirtError
from repos.domain.domain_common import guest_clean
from utils.utils import version_compare
from utils import utils

required_params = ('guestname', 'alias_type', 'user_alias')
optional_params = {'xml': 'xmls/detach_device_alias.xml',
                   'guestarch': 'x86_64',
                   'guestmachine': 'pc',
                   'video': 'qxl',
                   'graphic': 'spice'}


def check_result(dom, alias_type, user_alias_str, logger):
    time.sleep(10)
    xmlstr = dom.XMLDesc(0)

    alias_type_str = "</%s>" % alias_type
    if user_alias_str not in xmlstr and alias_type_str not in xmlstr:
        logger.info("not find %s and %s in xml." % (user_alias_str, alias_type_str))
        return 0
    else:
        logger.error("find %s or %s in xml." % (user_alias_str, alias_type_str))
        return 1


def detach_device_alias(params):
    """ Test detachDeviceAlias() """

    logger = params['logger']
    guestname = params['guestname']
    alias_type = params['alias_type']
    user_alias = params['user_alias']
    xmlstr = params.get('xml', 'xmls/detach_device_alias.xml')
    guestarch = params.get('guestarch', 'x86_64')
    guestmachine = params.get('guestmachine', 'pc')
    video = params.get('video', 'qxl')
    graphic = params.get('graphic', 'spice')

    if not version_compare("libvirt-python", 4, 4, 0, logger):
        logger.info("Current libvirt-python don't support "
                    "detachDeviceAlias().")
        return 0

    xmlstr = xmlstr.replace('GUESTARCH', guestarch)
    xmlstr = xmlstr.replace('GUESTMACHINE', guestmachine)
    xmlstr = xmlstr.replace('VIDEO', video)
    xmlstr = xmlstr.replace('GRAPHIC', graphic)

    user_alias_str = "ua-" + user_alias
    logger.info("alias type: %s" % alias_type)
    logger.info("user alias: %s" % user_alias_str)

    alias_str = "<alias name='%s'/></%s>" % (user_alias_str, alias_type)
    xmlstr = xmlstr.replace('</%s>' % alias_type, alias_str)
    logger.debug("xml:\n%s" % xmlstr)

    try:
        conn = libvirt.open()
        # if guest exist, clean it
        guest_clean(conn, guestname, logger)
        # define and start a new guest
        logger.info("define and start a guest with alias.")
        dom = conn.defineXML(xmlstr)
        dom.create()

        time.sleep(15)
        dom.detachDeviceAlias(user_alias_str, 0)
        if check_result(dom, alias_type, user_alias_str, logger):
            logger.error("FAIL: detach device alias failed.")
            return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    logger.info("PASS: detach device alias successful.")
    return 0


def detach_device_alias_clean(params):
    """
    Cleanup the test environment.
    """

    logger = params['logger']
    guestname = params['guestname']

    conn = libvirt.open()
    guest_clean(conn, guestname, logger)
    return 0
