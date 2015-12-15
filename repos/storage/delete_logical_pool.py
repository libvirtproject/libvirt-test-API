#!/usr/bin/env python
# Delete a storage pool of 'logical' type

import os
import re
import sys
import commands

import libvirt
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


def check_delete_pool(poolname):
    """Check delete storage pool result,
       /etc/lvm/backup/pool_name will not exist if pool delete is successful
    """
    path = "/etc/lvm/backup/%s" % poolname
    logger.debug("%s xml file path: %s" % (poolname, path))
    if os.access(path, os.R_OK):
        logger.debug("%s is still existing")
        return False
    else:
        logger.debug("%s file don't exist" % path)
        return True


def delete_logical_pool(params):
    """delete a storage pool"""
    global logger
    logger = params['logger']
    poolname = params['poolname']
    conn = sharedmod.libvirtobj['conn']

    if check_delete_pool(poolname):
        logger.debug("%s storage pool is deleted" % poolname)
        return 1

    display_pool_info(conn)
    display_physical_volume()

    try:
        logger.info("delete %s storage pool" % poolname)
        poolobj = conn.storagePoolLookupByName(poolname)
        poolobj.delete(0)
        display_pool_info(conn)
        display_physical_volume()

        if check_delete_pool(poolname):
            logger.info("delete %s storage pool is successful" % poolname)
        else:
            logger.error("fail to delete %s storage pool" % poolname)
            return 1
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
