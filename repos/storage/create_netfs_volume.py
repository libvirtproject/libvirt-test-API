#!/usr/bin/env python
# Creat volume for storage pool of 'netfs' type

import commands

from xml.dom import minidom
from libvirt import libvirtError
from src import sharedmod

required_params = ('poolname', 'volname', 'volformat', 'capacity',)
optional_params = {'xml': 'xmls/dir_volume.xml',
                   }


def get_pool_path(poolobj):
    """ get pool xml description """
    poolxml = poolobj.XMLDesc(0)

    logger.debug("the xml description of pool is %s" % poolxml)

    doc = minidom.parseString(poolxml)
    path_element = doc.getElementsByTagName('path')[0]
    textnode = path_element.childNodes[0]
    path_value = textnode.data

    return path_value


def virsh_vol_list(poolname):
    """using virsh command list the volume information"""

    shell_cmd = "virsh vol-list %s" % poolname
    (status, text) = commands.getstatusoutput(shell_cmd)
    logger.debug(text)


def create_netfs_volume(params):
    """create a volume in the netfs type of pool"""

    global logger
    logger = params['logger']
    poolname = params['poolname']
    volname = params['volname']
    volformat = params['volformat']
    capacity = params['capacity']
    xmlstr = params['xml']

    logger.info("the poolname is %s, volname is %s, \
                 volfomat is %s, capacity is %s" %
                (poolname, volname, volformat, capacity))

    conn = sharedmod.libvirtobj['conn']
    storage_pool_list = conn.listStoragePools()

    if poolname not in storage_pool_list:
        logger.error("pool %s doesn't exist or not running")
        return 1

    poolobj = conn.storagePoolLookupByName(poolname)

    path_value = get_pool_path(poolobj)

    volume_path = path_value + "/" + volname

    xmlstr = xmlstr.replace('VOLPATH', volume_path)
    xmlstr = xmlstr.replace('SUFFIX', capacity[-1])
    xmlstr = xmlstr.replace('CAP', capacity[:-1])

    logger.info("before create the new volume, current volume list is %s" %
                poolobj.listVolumes())

    logger.info("and using virsh command to \
                 ouput the volume information in the pool %s" % poolname)
    virsh_vol_list(poolname)

    logger.debug("volume xml:\n%s" % xmlstr)

    try:
        logger.info("create %s volume" % volname)
        poolobj.createXML(xmlstr, 0)
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    logger.info("volume create successfully, and output the volume information")
    virsh_vol_list(poolname)

    return 0
