#!/usr/bin/env python

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


def check_pool_create(conn, poolname, logger):
    """Check the result of create storage pool.  """
    pool_names = conn.listStoragePools()
    logger.info("poolnames is: %s " % pool_names)
    # check thru libvirt that it's really created..
    if poolname in pool_names:
        return True
    else:
        logger.info("check_pool_create %s storage pool is UNSUCCESSFUL!!" %
                    poolname)
        return False


def display_pool_info(conn, logger):
    """Display current storage pool information"""
    logger.debug(
        "current define storage pool: %s" %
        conn.listDefinedStoragePools())
    logger.debug("current active storage pool: %s" % conn.listStoragePools())


def create_iscsi_pool(params):
    """ Create a iscsi type storage pool from xml"""
    logger = params['logger']
    poolname = params['poolname']
    xmlstr = params['xml']

    conn = sharedmod.libvirtobj['conn']

    pool_names = conn.listDefinedStoragePools()
    pool_names += conn.listStoragePools()

    if poolname in pool_names:
        logger.error("%s storage pool has already been created" % poolname)
        return 1

    logger.debug("storage pool xml:\n%s" % xmlstr)

    try:
        logger.info("Creating %s storage pool" % poolname)
        conn.storagePoolCreateXML(xmlstr, 0)
        display_pool_info(conn, logger)
        if check_pool_create(conn, poolname, logger):
            logger.info("creating %s storage pool is SUCCESSFUL!!!" % poolname)
        else:
            logger.info(
                "creating %s storage pool is UNSUCCESSFUL!!!" %
                poolname)
            return 1
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
