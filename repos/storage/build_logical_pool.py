#!/usr/bin/env python

import os

from libvirt import libvirtError
from src import sharedmod
from utils import process

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
    ret1 = process.run("pvdisplay", shell=True, ignore_status=True)
    if ret1.exit_status == 0:
        logger.debug("pvdisplay command executes successfully")
        logger.debug(ret1.stdout)
    else:
        logger.error("fail to execute pvdisplay command")

    ret2 = process.run("vgdisplay", shell=True, ignore_status=True)
    if ret2.exit_status == 0:
        logger.debug("vgdisplay command executes successfully")
        logger.debug(ret2.stdout)
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
        ret = process.run("grep vgcreate %s" % path, shell=True, ignore_status=True)
        logger.debug(ret.stdout)
        if ret.exit_status == 0:
            return True
        else:
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
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
