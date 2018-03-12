#!/usr/bin/env python
# Create a logical type storage volume

import os

from xml.dom import minidom
from libvirt import libvirtError
from src import sharedmod
from utils import utils, process

required_params = ('poolname', 'volname', 'capacity',)
optional_params = {'xml': 'xmls/logical_volume.xml',
                   }


def get_pool_path(poolobj):
    """ Get pool target path """
    poolxml = poolobj.XMLDesc(0)

    logger.debug("the xml description of pool is %s" % poolxml)

    doc = minidom.parseString(poolxml)
    path_element = doc.getElementsByTagName('path')[0]
    textnode = path_element.childNodes[0]
    return textnode.data


def display_volume_info(poolobj):
    """Display current storage volume information"""
    logger.debug("current created storage volume: %s"
                 % poolobj.listVolumes())


def display_physical_volume():
    """Display current physical volume information"""
    ret = process.run("lvdisplay", shell=True, ignore_status=True)
    logger.debug("lvdisplay return value: %d" % ret.exit_status)
    logger.debug("lvdisplay output: %s" % ret.stdout)


def get_storage_volume_number(poolobj):
    """Get storage volume number"""
    vol_num = poolobj.numOfVolumes()
    logger.info("current storage volume number: %s" % vol_num)
    return vol_num


def check_volume_create(poolobj, poolname, volname, size):
    """Check storage volume result, poolname will exist under
       /etc/lvm/backup/ and lvcreate command is called if
       volume creation is successful
    """
    path = "/etc/lvm/backup/%s" % poolname
    logger.debug("%s file path: %s" % (poolname, path))
    if os.access(path, os.R_OK):
        logger.debug("execute grep lvcreate %s command" % path)
        cmd = ("grep 'lvcreate --name %s -L %sK .*%s' %s" %
               (volname, size, poolname, path))
        ret = process.run(cmd, shell=True, ignore_status=True)
        logger.debug(ret.stdout)
        if ret.exit_status == 0 and volname in poolobj.listVolumes():
            return True
        else:
            return False
    else:
        logger.debug("%s file don't exist" % path)
        return False


def create_logical_volume(params):
    """Create a logical type storage volume from xml"""
    global logger
    logger = params['logger']
    poolname = params['poolname']
    volname = params['volname']
    capacity = int(params['capacity'])
    xmlstr = params['xml']

    conn = sharedmod.libvirtobj['conn']
    pool_names = conn.listDefinedStoragePools()
    pool_names += conn.listStoragePools()

    if poolname in pool_names:
        poolobj = conn.storagePoolLookupByName(poolname)
    else:
        logger.error("%s not found\n" % poolname)
        return 1

    if not poolobj.isActive():
        logger.error("%s pool is inactive" % poolname)
        return 1

    poolpath = get_pool_path(poolobj)
    logger.debug("pool target path: %s" % poolpath)
    volpath = "%s/%s" % (poolpath, volname)
    xmlstr = xmlstr.replace('TARGETPATH', volpath)
    logger.debug("volume target path: %s" % volpath)

    logger.debug("storage volume xml:\n%s" % xmlstr)

    vol_num1 = get_storage_volume_number(poolobj)
    display_volume_info(poolobj)
    display_physical_volume()

    try:
        logger.info("create %s storage volume" % volname)
        poolobj.createXML(xmlstr, 0)
        display_physical_volume()
        vol_num2 = get_storage_volume_number(poolobj)
        display_volume_info(poolobj)
        if check_volume_create(poolobj, poolname, volname, capacity * 1024) \
                and vol_num2 > vol_num1:
            logger.info("create %s storage volume is successful" % volname)
        else:
            logger.error("fail to crearte %s storage volume" % volname)
            return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
