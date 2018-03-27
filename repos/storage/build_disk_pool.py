#!/usr/bin/env python

import time
from xml.dom import minidom

import libvirt
from libvirt import libvirtError
from utils import process
from src import sharedmod

required_params = ('poolname',)
optional_params = {'flags': 'no_override'}


def parse_flags(logger, params):
    flags = params.get('flags', 'no_override')
    logger.info('flags :%s' % flags)
    if flags == 'none':
        return 0
    elif flags == 'no_override':
        return libvirt.VIR_STORAGE_POOL_BUILD_NO_OVERWRITE
    elif flags == 'override':
        return libvirt.VIR_STORAGE_POOL_BUILD_OVERWRITE
    else:
        logger.error("flag is illegal.")
        return -1


def get_pool_devicename_type(poolobj):
    """ get device name and partition table of the pool
        from its xml description """
    poolxml = poolobj.XMLDesc(0)

    logger.debug("the xml description of pool is %s" % poolxml)

    doc = minidom.parseString(poolxml)
    device_element = doc.getElementsByTagName('device')[0]
    source_device = device_element.attributes['path'].value

    format_element = doc.getElementsByTagName('format')[0]
    device_type = format_element.attributes['type'].value

    return source_device, device_type


def check_pool_built(source_device, device_type):
    """using parted command tool to check the validation of final result"""

    cmd = "parted -s %s print" % source_device
    output = process.system_output(cmd, shell=True, ignore_status=True)
    partition_info = output.split("\n")[3]

    logger.debug("the partition information is %s" % partition_info)
    partition_table = partition_info.split(": ")[1]

    if device_type in partition_table:
        return 0
    else:
        return 1


def build_disk_pool(params):
    """ build a defined and inactive pool"""

    global logger
    logger = params['logger']
    poolname = params['poolname']
    logger.info("the poolname is %s" % (poolname))
    flag = parse_flags(logger, params)
    conn = sharedmod.libvirtobj['conn']
    if flag == -1:
        return 1

    pool_names = conn.listDefinedStoragePools()
    pool_names += conn.listStoragePools()

    if poolname in pool_names:
        poolobj = conn.storagePoolLookupByName(poolname)
    else:
        logger.error("%s not found\n" % poolname)
        return 1

    if poolobj.isActive():
        logger.error("%s is active already" % poolname)
        return 1

    source_device, device_type = get_pool_devicename_type(poolobj)
    logger.info("the source device of the pool is %s, \
                 the partition table type is %s" %
                (source_device, device_type))

    try:
        logger.info("begin to build the storage pool")
        poolobj.build(flag)
        time.sleep(5)
        if not check_pool_built(source_device, device_type):
            logger.info("building %s storage pool is SUCCESSFUL!!!" % poolname)
        else:
            logger.info("building %s storage pool is UNSUCCESSFUL!!!" %
                        poolname)
            return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    return 0
