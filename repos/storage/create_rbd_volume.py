#!/usr/bin/env python
# Creat volume for storage pool of 'rbd' type

import commands

from xml.dom import minidom
from libvirt import libvirtError
from src import sharedmod

required_params = ('poolname', 'volname', 'cephserver', 'cephserverpool',)
optional_params = {'xml': 'xmls/rbd_volume.xml',
                   'suffix': 'bytes',
                   'capacity': '1073741824',
                   'allocation': '1073741824',
                   }


def create_rbd_volume(params):
    """create a volume in the rbd type of pool"""

    global logger
    logger = params['logger']
    poolname = params['poolname']
    volname = params['volname']
    xmlstr = params['xml']

    logger.info("the poolname is %s, volname is %s" %
                (poolname, volname))

    try:
        conn = sharedmod.libvirtobj['conn']
        storage_pool_list = conn.listStoragePools()

        if poolname not in storage_pool_list:
            logger.error("pool %s doesn't exist or not running")
            return 1

        poolobj = conn.storagePoolLookupByName(poolname)
        logger.info("before create the new volume, current volume list is %s" %
                    poolobj.listVolumes())
        logger.debug("volume xml:\n%s" % xmlstr)
        logger.info("create %s volume" % volname)
        poolobj.createXML(xmlstr, 0)
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    logger.info("volume create successfully, and output the volume information")
    logger.info("after create the new volume, current volume list is %s" %
                poolobj.listVolumes())

    return 0


def create_rbd_volume_clean(params):
    global logger
    logger = params['logger']
    poolname = params['poolname']
    volname = params['volname']
    cephserver = params['cephserver']
    cephserverpool = params['cephserverpool']

    conn = sharedmod.libvirtobj['conn']
    poollist = conn.listDefinedStoragePools()
    if poolname in poollist:
        poolobj = conn.storagePoolLookupByName(poolname)
        vollist = poolobj.listVolumes()
        if volname in vollist:
            volobj = poolobj.storageVolLookupByName(volname)
            volobj.delete(0)

    cmd = "rbd -m %s -p %s rm %s" % (cephserver, cephserverpool, volname)
    (stat, ret) = commands.getstatusoutput(cmd)
    if stat:
        logger.debug(ret)
