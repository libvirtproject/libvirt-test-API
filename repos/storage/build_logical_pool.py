#!/usr/bin/env python

import os
import commands

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


def display_physical_volume():
    """Display volume group and physical volume information"""
    stat1, ret1 = commands.getstatusoutput("pvdisplay")
    if stat1 == 0:
        logger.debug("pvdisplay command executes successfully")
        logger.debug(ret1)
    else:
        logger.error("fail to execute pvdisplay command")

    stat2, ret2 = commands.getstatusoutput("vgdisplay")
    if stat2 == 0:
        logger.debug("vgdisplay command executes successfully")
        logger.debug(ret2)
    else:
        logger.error("fail to execute pvdisplay command")


def check_build_pool(poolname):
    """Check build storage pool result, poolname will exist under
       /etc/lvm/backup/ if pool build is successful
    """
    path = "/etc/lvm/backup/%s" % poolname
    logger.debug("%s xml file path: %s" % (poolname, path))
    if os.access(path, os.R_OK):
        logger.debug("execute grep vgcreate %s command" % path)
        stat, ret = commands.getstatusoutput("grep vgcreate %s" % path)
        if stat == 0:
            logger.debug(ret)
            return True
        else:
            logger.debug(ret)
            return False
    else:
        logger.debug("%s file don't exist" % path)
        return False


def build_logical_pool(params):
    """Build a storage pool"""
    global logger
    logger = params['logger']
    poolname = params['poolname']
    conn = sharedmod.libvirtobj['conn']

    if check_build_pool(poolname):
        logger.debug("%s storage pool is built" % poolname)
        return 1

    display_pool_info(conn)
    display_physical_volume()

    try:
        logger.info("build %s storage pool" % poolname)
        poolobj = conn.storagePoolLookupByName(poolname)
        poolobj.build(0)
        display_pool_info(conn)
        display_physical_volume()

        if check_build_pool(poolname):
            logger.info("build %s storage pool is successful" % poolname)
        else:
            logger.error("fail to build %s storage pool" % poolname)
            return 1
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
