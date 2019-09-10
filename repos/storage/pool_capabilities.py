#!/usr/bin/env python
# Get capabilities of storage pool support

import lxml
import libvirt

from utils import utils
from libvirt import libvirtError

required_params = ()
optional_params = {}


def check_capabilities(capabilities, logger):
    pool_tree = lxml.etree.fromstring(capabilities)
    pool_type_list = dict(zip(pool_tree.xpath("//pool/@type"), pool_tree.xpath("//pool/@supported")))
    logger.info("Pool type list: %s" % pool_type_list)
    pool_type = []
    for key, value in pool_type_list.items():
        if value == "yes":
            pool_type.append(key)
    logger.info("Supported pool type: %s" % pool_type)

    storage_conn = libvirt.open("storage:///system")
    capabilities_tree = lxml.etree.fromstring(storage_conn.getCapabilities())
    capabilities_value = capabilities_tree.xpath("///value/text()")
    logger.info("Get storage capabilities from connect: %s" % capabilities_value)
    pool_type.sort()
    capabilities_value.sort()
    if pool_type == capabilities_value:
        return 0
    else:
        return 1


def pool_capabilities(params):
    """ Get capabilities of storage pool support """
    logger = params['logger']

    if not utils.version_compare('libvirt-python', 5, 6, 0, logger):
        logger.info("Current libvirt-python don't support getStoragePoolCapabilities().")
        return 0

    try:
        conn = libvirt.open()
        capabilities = conn.getStoragePoolCapabilities()
        logger.info("pool capabilities: %s" % capabilities)
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    if check_capabilities(capabilities, logger):
        logger.error("FAIL: Get pool capabilities failed.")
        return 1

    logger.info("PASS: Get pool capabilities successful.")
    return 0
