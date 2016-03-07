#!/usr/bin/evn python

import os
import libvirt
from libvirt import libvirtError
from xml.dom import minidom

from utils import utils

from src import sharedmod

required_params = ('poolname',)
optional_params = {}


def get_disk_partition_list(pool_obj):
    """
        Get the partition list of disk type storage pool
    """
    poolxml = pool_obj.XMLDesc(0)

    doc = minidom.parseString(poolxml)
    device_element = doc.getElementsByTagName('device')[0]
    device_path = device_element.attributes['path'].value
    device_name = device_path.split('/')[-1]
    logger.debug("device path is %s" % device_path)

    get_partition_cmd = "cat /proc/partitions | grep " + device_name
    (status, partition_info) = utils.exec_cmd(get_partition_cmd, shell=True)

    if status:
        logger.error("Executing " + get_partition_cmd + " failed")
        return False, []
    else:
        logger.debug("the partition inforamtion is %s " % partition_info)

        partition_list = partition_info[1:]
        partition_list = [partition_list[i].split(' ')[-1]
                          for i in range(len(partition_list))]

        logger.info("the partition list is %s" % partition_list)
        return True, partition_list


def get_pool_path_type(pool_obj):
    """
        Get the pool path and type
    """
    poolxml = pool_obj.XMLDesc(0)
    logger.debug("the xml description of pool is %s" % poolxml)

    doc = minidom.parseString(poolxml)
    path_element = doc.getElementsByTagName('path')[0]
    textnode = path_element.childNodes[0]
    path_value = textnode.data

    type_element = doc.getElementsByTagName('pool')[0]
    type_value = type_element.attributes['type'].value

    return path_value, type_value


def check_list_volumes(pool_obj, vol_name_list):
    """
        Check the result of listAllVolumes
    """
    vol_poolobj_list = pool_obj.listVolumes()
    logger.debug("get volumes from listVolumes is %s" % vol_poolobj_list)

    poolpath, pooltype = get_pool_path_type(pool_obj)
    logger.info("the pool path is %s" % poolpath)
    logger.info("the pool type is %s" % pooltype)

    if pooltype in ['dir', 'netfs', 'logical', 'fs']:
        if not os.path.exists(poolpath):
            vol_cmd_list = []
        else:
            get_vol_cmd = "ls -A " + poolpath
            (status, vol_cmd_list) = utils.exec_cmd(get_vol_cmd, shell=True)
            if status:
                logger.error("Executing " + get_vol_cmd + " failed")
                logger.error(get_vol_cmd)
                return False
    elif pooltype == 'disk':
        (status, vol_cmd_list) = get_disk_partition_list(pool_obj)
        if status is False:
            return False
    elif pooltype in ['iscsi', 'scsi', 'mpath']:
        if (cmp(vol_poolobj_list, vol_name_list) == 0):
            return True
        else:
            return False
    else:
        logger.error("Cannot recognize pooltype: %s" % pooltype)
        return False

    logger.debug("get volumes from poolpath is %s" % vol_cmd_list)
    logger.info("compare the volume list under poolpath and list from API")
    vol_name_list.sort()
    vol_poolobj_list.sort()
    vol_cmd_list.sort()
    if (cmp(vol_poolobj_list, vol_name_list) == 0) and \
            (cmp(vol_name_list, vol_cmd_list) == 0):
        return True
    else:
        return False


def list_volumes(params):
    """
        List all the volumes of a storage pool
    """
    global logger
    logger = params['logger']
    poolname = params['poolname']
    vol_name_list = []

    logger.info("the poolname is %s" % (poolname))
    conn = sharedmod.libvirtobj['conn']
    storage_pool_list = conn.listStoragePools()

    if poolname not in storage_pool_list:
        logger.error("pool %s doesn't exist or not running" % poolname)
        return 1

    pool_obj = conn.storagePoolLookupByName(poolname)

    try:
        vol_obj_list = pool_obj.listAllVolumes()
        for vol_obj in vol_obj_list:
            vol_name_list.append(vol_obj.name())
        logger.info("the volume list is %s" % vol_name_list)

        if check_list_volumes(pool_obj, vol_name_list):
            logger.info("get the right volumes list successfully")
        else:
            logger.error("fail to get the right volumes list")
            return 1

    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
