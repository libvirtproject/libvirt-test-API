#!/usr/bin/env python

import time

from libvirt import libvirtError
from src import sharedmod
from utils import utils

required_params = ('poolname',)
optional_params = {'flags': ''}


def activate_pool(params):
    """activate a storage pool that's been defined
       and inactive
    """
    logger = params['logger']
    poolname = params['poolname']
    flag = utils.parse_flags(params)
    if flag == -1:
        return 1

    conn = sharedmod.libvirtobj['conn']
    try:
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

        poolobj.create(flag)
        time.sleep(5)
        if poolobj.isActive():
            logger.info("activating %s storage pool is SUCCESSFUL!!!" %
                        poolname)
        else:
            logger.info("activating %s storage pool is UNSUCCESSFUL!!!" %
                        poolname)
            return 1

    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    return 0
