#!/usr/bin/env python

import os

from xml.dom import minidom
from libvirt import libvirtError
from src import sharedmod

required_params = ('poolname',)
optional_params = {}


def display_pool_info(conn):
    """Display current storage pool information"""
    logger.debug("current define storage pool: %s"
                 % conn.listDefinedStoragePools())
    logger.debug("current active storage pool: %s"
                 % conn.listStoragePools())


def check_build_pool(path):
    """Check poolname directory if exist, it will exist
       directory if the directory has ever be created or
       pool building is successful
    """
    if os.access(path, os.R_OK):
        logger.debug("%s directory is existent" % path)
        return True
    else:
        logger.debug("%s directory don't exist" % path)
        return False


def build_netfs_pool(params):
    """Build a storage pool"""
    global logger
    logger = params['logger']
    poolname = params['poolname']
    conn = sharedmod.libvirtobj['conn']

    defined_pool_list = conn.listDefinedStoragePools()
    if poolname not in defined_pool_list:
        logger.error("the pool %s is active or undefine" % poolname)
        return 1

    poolobj = conn.storagePoolLookupByName(poolname)

    pool_xml = poolobj.XMLDesc(0)
    doc = minidom.parseString(pool_xml)
    unicode_path_value = doc.getElementsByTagName("path")[0].firstChild.data
    path_value = unicode_path_value.encode()

    if check_build_pool(path_value):
        logger.debug("%s directory has be built" % path_value)

    display_pool_info(conn)

    try:
        logger.info("build %s storage pool" % poolname)
        poolobj.build(0)
        display_pool_info(conn)

        if check_build_pool(path_value):
            logger.info("build %s storage pool is successful" % poolname)
        else:
            logger.error("fail to build %s storage pool" % poolname)
            return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    return 0
