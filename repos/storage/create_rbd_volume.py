#!/usr/bin/env python
# Creat volume for storage pool of 'rbd' type

from libvirt import libvirtError
from src import sharedmod
from utils import process

required_params = ('poolname', 'volname', 'cephserver', 'cephserverpool',)
optional_params = {'xml': 'xmls/rbd_volume.xml',
                   'suffix': 'bytes',
                   'capacity': '1073741824',
                   'allocation': '1073741824',
                   }


def check_volume_from_server(poolname, volname, cephserver, cephserverpool, logger):
    cmd = "rbd -m %s -p %s ls | grep %s" % (cephserver, cephserverpool, volname)
    ret = process.run(cmd, shell=True, ignore_status=True)
    if not ret.exit_status:
        logger.info("%s already exist in ceph server, remove it." % volname)
        cmd = "rbd -m %s -p %s rm %s" % (cephserver, cephserverpool, volname)
        ret = process.run(cmd, shell=True, ignore_status=True)
        if ret.exit_status:
            logger.info("Remove %s failed." % volname)
            logger.debug(ret.stdout)
            return 1

    return 0


def check_volume_from_pool(poolobj, volname, logger):
    vol_list = poolobj.listVolumes()
    if volname in vol_list:
        logger.info("%s already exist in pool, remove it." % volname)
        volobj = poolobj.storageVolLookupByName(volname)
        volobj.delete(0)

    return 0


def create_rbd_volume(params):
    """create a volume in the rbd type of pool"""
    logger = params['logger']
    poolname = params['poolname']
    volname = params['volname']
    xmlstr = params['xml']
    cephserver = params['cephserver']
    cephserverpool = params['cephserverpool']

    logger.info("the poolname is %s, volname is %s" %
                (poolname, volname))
    if check_volume_from_server(poolname, volname, cephserver, cephserverpool, logger):
        return 1

    try:
        conn = sharedmod.libvirtobj['conn']
        storage_pool_list = conn.listStoragePools()

        if poolname not in storage_pool_list:
            logger.error("pool %s doesn't exist or not running" % poolname)
            return 1

        poolobj = conn.storagePoolLookupByName(poolname)
        if check_volume_from_pool(poolobj, volname, logger):
            return 1
        logger.info("before create the new volume, current volume list is %s" %
                    poolobj.listVolumes())
        logger.debug("volume xml:\n%s" % xmlstr)
        logger.info("create %s volume" % volname)
        poolobj.createXML(xmlstr, 0)
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    logger.info("volume create successfully, and output the volume information")
    logger.info("after create the new volume, current volume list is %s" %
                poolobj.listVolumes())

    return 0


def create_rbd_volume_clean(params):
    logger = params['logger']
    poolname = params['poolname']
    volname = params['volname']
    cephserver = params['cephserver']
    cephserverpool = params['cephserverpool']

    conn = sharedmod.libvirtobj['conn']
    poollist = conn.listStoragePools()
    logger.debug("poollist : %s" % poollist)
    if poolname in poollist:
        poolobj = conn.storagePoolLookupByName(poolname)
        vollist = poolobj.listVolumes()
        logger.debug("vollist : %s" % vollist)
        if volname in vollist:
            volobj = poolobj.storageVolLookupByName(volname)
            volobj.delete(0)

    cmd = "rbd -m %s -p %s rm %s" % (cephserver, cephserverpool, volname)
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.debug(ret.stdout)
