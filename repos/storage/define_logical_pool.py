#!/usr/bin/env python
# Define a storage pool of 'logical' type

import os

from libvirt import libvirtError
from src import sharedmod
from repos.storage import storage_common
from utils import utils

required_params = ('poolname', 'sourcename', 'sourcepath',
                   'portal', 'wwn')
optional_params = {'sourceformat': 'lvm2',
                   'xml': 'xmls/logical_pool.xml',
                   }


def define_logical_pool(params):
    """Define a logical type storage pool from xml"""
    logger = params['logger']
    poolname = params['poolname']
    xmlstr = params['xml']

    conn = sharedmod.libvirtobj['conn']

    if not storage_common.check_pool(conn, poolname, logger):
        logger.error("%s storage pool is defined" % poolname)
        return 1

    logger.debug("storage pool xml:\n%s" % xmlstr)

    pool_num1 = conn.numOfDefinedStoragePools()
    logger.info("original storage pool define number: %s" % pool_num1)
    storage_common.display_pool_info(conn, logger)

    try:
        # Prepare the disk
        portal = params.get("portal", "127.0.0.1")
        wwn = params.get("wwn")
        src_path = params.get("sourcepath", "/dev/sdb1")
        if not os.path.exists(src_path):
            if not storage_common.prepare_iscsi_disk(portal, wwn, logger):
                logger.error("Failed to prepare iscsi disk")
                return 1
            if not utils.wait_for(lambda: os.path.exists(src_path[:-1]), 5):
                logger.error("Target device didn't show up")
                return 1
        if not storage_common.prepare_partition(src_path, logger):
            logger.error("Failed to prepare partition")
            return 1
        logger.info("define %s storage pool" % poolname)
        conn.storagePoolDefineXML(xmlstr, 0)
        pool_num2 = conn.numOfDefinedStoragePools()
        logger.info("current storage pool define number: %s" % pool_num2)
        storage_common.display_pool_info(conn, logger)
        if storage_common.check_pool_define(poolname, logger) and pool_num2 > pool_num1:
            logger.info("define %s storage pool is successful" % poolname)
        else:
            logger.error("%s storage pool is undefined" % poolname)
            return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    return 0
