#!/usr/bin/env python
# Delete a volume from netfs type storage pool

import os

from libvirt import libvirtError
from src import sharedmod

required_params = ('poolname', 'volname',)
optional_params = {}


def display_volume_info(poolobj):
    """Display current storage volume information"""
    logger.debug("current storage volume list: %s"
                 % poolobj.listVolumes())


def get_storage_volume_number(poolobj):
    """Get storage volume number"""
    vol_num = poolobj.numOfVolumes()
    logger.info("current storage volume number: %s" % vol_num)
    return vol_num


def check_volume_delete(volkey):
    """Check storage volume result, volname {volkey} will don't exist
       if deleting volume is successful
    """
    logger.debug("volume file path: %s" % volkey)
    if not os.access(volkey, os.R_OK):
        return True
    else:
        logger.debug("%s file don't exist" % volkey)
        return False


def delete_netfs_volume(params):
    """Delete a netfs type storage volume"""
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
        logger.error("can't delete volume from inactive %s pool" % poolname)
        return 1

    volobj = poolobj.storageVolLookupByName(volname)
    volkey = volobj.key()
    logger.debug("volume key: %s" % volkey)

    vol_num1 = get_storage_volume_number(poolobj)
    display_volume_info(poolobj)

    try:
        logger.info("delete %s storage volume" % volname)
        volobj.delete(0)
        vol_num2 = get_storage_volume_number(poolobj)
        display_volume_info(poolobj)
        if check_volume_delete(volkey) and vol_num1 > vol_num2:
            logger.info("delete %s storage volume is successful" % volname)
        else:
            logger.error("%s storage volume is undeleted" % volname)
            return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    return 0
