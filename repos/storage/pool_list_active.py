#!/usr/bin/env python
# list active storage pool testing with flag:
# libvirt.VIR_CONNECT_LIST_STORAGE_POOLS_ACTIVE

import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ()
optional_params = {
}


def pool_list_active(params):
    """list active storage pool testing"""

    global logger
    logger = params['logger']
    namelist = []

    conn = sharedmod.libvirtobj['conn']
    try:
        pool_num = conn.numOfStoragePools()
        logger.info("number of active storage pools is %s" % pool_num)

        flag = libvirt.VIR_CONNECT_LIST_STORAGE_POOLS_ACTIVE
        poolobj_list = conn.listAllStoragePools(flag)
        if not len(poolobj_list) == pool_num:
            logger.error("active pool object number mismatched")
            return 1

        for i in poolobj_list:
            pool_name = i.name()
            namelist.append(pool_name)

        logger.info("active pool name list is %s" % namelist)

        active_namelist = conn.listStoragePools()
        if namelist == active_namelist:
            logger.info("active pool name list matched")
        else:
            logger.error("active pool name list mismatched")
            return 1

    except libvirtError, e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    logger.info("list active storage pool succeed")
    return 0
