#!/usr/bin/env python
# Delete a logical type storage volume

import os
import re
import sys
import commands

import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ('poolname', 'volname',)
optional_params = {}


def display_volume_info(poolobj):
    """Display current storage volume information"""
    logger.info("current storage volume list: %s"
                % poolobj.listVolumes())


def display_physical_volume():
    """Display current physical storage volume information"""
    stat, ret = commands.getstatusoutput("lvdisplay")
    logger.debug("lvdisplay command execute return value: %d" % stat)
    logger.debug("lvdisplay command execute return result: %s" % ret)


def get_storage_volume_number(poolobj):
    """Get storage volume number"""
    vol_num = poolobj.numOfVolumes()
    logger.info("current storage volume number: %s" % vol_num)
    return vol_num


def check_volume_delete(poolname, volkey):
    """Check storage volume result, poolname will exist under
       /etc/lvm/backup/ and lvdelete command is called if
       volume creation is successful
    """
    path = "/etc/lvm/backup/%s" % poolname
    logger.debug("%s file path: %s" % (poolname, path))
    if os.access(path, os.R_OK):
        logger.debug("execute grep lvremove %s command" % path)
        cmd = "grep 'lvremove' %s" % (path)
        logger.debug(cmd)
        stat, ret = commands.getstatusoutput(cmd)
        if stat == 0:
            logger.debug(ret)
            return True
        else:
            logger.debug(ret)
            return False
    else:
        logger.debug("%s file don't exist" % path)
        return False


def delete_logical_volume(params):
    """Create a logical type storage volume"""
    global logger
    logger = params['logger']
    poolname = params['poolname']
    volname = params['volname']
    conn = sharedmod.libvirtobj['conn']

    pool_names = conn.listDefinedStoragePools()
    pool_names += conn.listStoragePools()

    if poolname in pool_names:
        poolobj = conn.storagePoolLookupByName(poolname)
    else:
        logger.error("%s not found\n" % poolname)
        return 1

    if not poolobj.isActive():
        logger.debug("%s pool is inactive" % poolname)
        return 1

    volobj = poolobj.storageVolLookupByName(volname)
    volkey = volobj.key()
    logger.debug("volume key: %s" % volkey)

    vol_num1 = get_storage_volume_number(poolobj)
    display_volume_info(poolobj)
    display_physical_volume()

    try:
        logger.info("delete %s storage volume" % volname)
        volobj.delete(0)
        vol_num2 = get_storage_volume_number(poolobj)
        display_volume_info(poolobj)
        display_physical_volume()

        if vol_num1 > vol_num2 and check_volume_delete(poolname, volkey):
            logger.info("delete %s storage volume is successful" % volname)
        else:
            logger.error("fail to delete %s storage volume" % volname)
            return 1
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
