#!/usr/bin/env python
# Delete a logical type storage volume

import os

from libvirt import libvirtError
from src import sharedmod
from utils import process

required_params = ('poolname', 'volname',)
optional_params = {}


def display_volume_info(poolobj):
    """Display current storage volume information"""
    logger.info("current storage volume list: %s"
                % poolobj.listVolumes())


def display_physical_volume():
    """Display current physical storage volume information"""
    ret = process.run("lvdisplay", shell=True, ignore_status=True)
    logger.debug("lvdisplay return value: %d" % ret.exit_status)
    logger.debug("lvdisplay output: %s" % ret.stdout)


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
        ret = process.run(cmd, shell=True, ignore_status=True)
        logger.debug(ret.stdout)
        if ret.exit_status == 0:
            return True
        else:
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
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
