#!/usr/bin/env python
# Define a storage pool of 'disk' type

from libvirt import libvirtError
from src import sharedmod
from repos.storage import storage_common

required_params = ('poolname', 'sourcepath',)
optional_params = {'sourceformat': 'dos',
                   'targetpath': '/dev',
                   'xml': 'xmls/disk_pool.xml',
                   }


def define_disk_pool(params):
    """Define a disk type storage pool from xml"""

    global logger
    logger = params['logger']
    poolname = params['poolname']
    sourcepath = params['sourcepath']
    xmlstr = params['xml']

    logger.info("the poolname is %s, pooltype is disk, sourcepath is %s" %
                (poolname, sourcepath))

    conn = sharedmod.libvirtobj['conn']

    if not storage_common.check_pool(conn, poolname, logger):
        logger.error("%s storage pool is defined" % poolname)
        return 1

    logger.debug("storage pool xml:\n%s" % xmlstr)

    pool_num1 = conn.numOfDefinedStoragePools()
    logger.info("original storage pool define number: %s" % pool_num1)
    storage_common.display_pool_info(conn, logger)

    try:
        logger.info("define %s storage pool" % poolname)
        conn.storagePoolDefineXML(xmlstr, 0)
        pool_num2 = conn.numOfDefinedStoragePools()
        logger.info("current storage pool define number: %s" % pool_num2)
        storage_common.display_pool_info(conn, logger)
        if storage_common.check_pool_define(poolname, logger) and pool_num2 > pool_num1:
            logger.info("It is successful to define %s storage pool" % poolname)
        else:
            logger.error("%s storage pool was not defined successfully" %
                         poolname)
            return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
