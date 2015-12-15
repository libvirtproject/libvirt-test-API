#!/usr/bin/env python
# Define a storage pool of 'iscsi' type

import os
import re
import sys

import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ('poolname', 'sourcehost', 'sourcepath',)
optional_params = {'targetpath': '/dev/disk/by-path',
                   'xml': 'xmls/iscsi_pool.xml',
                   }


def display_pool_info(conn, logger):
    """Display current storage pool information"""
    logger.debug(
        "current define storage pool: %s" %
        conn.listDefinedStoragePools())
    logger.debug("current active storage pool: %s" % conn.listStoragePools())


def check_pool_define(conn, poolname, logger):
    """Check define storage pool result, if define storage is successful,
       poolname.xml will exist under /etc/libvirt/storage/
       and can use virt-xml-validate tool to check the file validity
    """
    path = "/etc/libvirt/storage/%s.xml" % poolname
    logger.debug("%s xml file path: %s" % (poolname, path))
    pool_names = conn.listDefinedStoragePools()
    if os.access(path, os.R_OK):
        logger.debug("Check: %s does exist." % path)
        # check thru libvirt that it's really defined..
        try:
            pool_names.index(poolname)
        except ValueError:
            logger.info("define %s storage pool is UNSUCCESSFUL!!" % poolname)
            return False
        return True
    else:
        return False


def define_iscsi_pool(params):
    """
    Defines a iscsi based storage pool from xml.
    """
    logger = params['logger']
    poolname = params['poolname']
    xmlstr = params['xml']

    conn = sharedmod.libvirtobj['conn']

    if check_pool_define(conn, poolname, logger):
        logger.error("%s storage pool is ALREADY defined" % poolname)
        return 1

    logger.debug("storage pool xml:\n%s" % xmlstr)

    pool_num1 = conn.numOfDefinedStoragePools()
    logger.info("original storage pool define number: %s" % pool_num1)
    display_pool_info(conn, logger)

    try:
        logger.info("define %s storage pool" % poolname)
        conn.storagePoolDefineXML(xmlstr, 0)
        pool_num2 = conn.numOfDefinedStoragePools()
        logger.info("current storage pool define number: %s" % pool_num2)
        display_pool_info(conn, logger)
        if check_pool_define(conn, poolname, logger) and pool_num2 > pool_num1:
            logger.info("define %s storage pool is successful" % poolname)
        else:
            logger.error("%s storage pool is undefined" % poolname)
            return 1
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
