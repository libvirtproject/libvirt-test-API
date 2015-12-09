#!/usr/bin/env python
#test storagePoolLookupByVolume() API for libvirt

import os
import libvirt
from libvirt import libvirtError
from src import sharedmod

required_params = ('poolname','volname',)
optional_params = {}

def pool_lookup_by_volume(params):
    """
       test API for storagePoolLookupByVolume in class virStoragePool
    """
    logger = params['logger']
    poolname = params['poolname']
    volname = params['volname']
    logger.info("The given pool name is %s" % (poolname))
    logger.info("The given vol name is %s" % (volname))
    conn = sharedmod.libvirtobj['conn']
    pool = conn.storagePoolLookupByName(poolname)
    pre_vol = pool.storageVolLookupByName(volname)
    volpath = pre_vol.path()
    logger.info("The given volume path is %s" % (volpath))
    temp = volpath.split("/")
    temp.pop(0)
    temp.pop(-1)
    temp1 = "/" + "/".join(temp)
    if not os.path.exists(temp1):
        logger.warning("volume path file %s is not exist" % temp1)

    try:
        vol = conn.storageVolLookupByPath(volpath)
        pool_name = vol.storagePoolLookupByVolume().name()
        logger.info("The pool name is %s from API" % (pool_name))

        if not pool_name == poolname:
            return 1

    except libvirtError, e:
        logger.error("API error message: %s, error code is %s" \
                     % (e.message, e.get_error_code()))
        return 1

    return 0
