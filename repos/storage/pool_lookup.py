#!/usr/bin/env python
# storage pool lookup testing

import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ('poolname',)
optional_params = {
                   'volname': None
                  }

def pool_lookup(params):
    """storage pool lookup testing"""

    global logger
    logger = params['logger']
    poolname = params['poolname']
    volname = params.get('volname')
    retval = 0

    logger.info("the poolname is %s" % poolname)
    if volname:
        logger.info("the given volume name is %s" % volname)

    conn = sharedmod.libvirtobj['conn']
    try:
        logger.info("lookup the pool object by name: %s" % poolname)
        poolobj = conn.storagePoolLookupByName(poolname)
        if poolobj.name() == poolname:
            logger.info("pool object lookup by name succeed")
        else:
            logger.error("pool object lookup by name failed")
            retval += 1

        uuid = poolobj.UUID()
        #logger.info("lookup the pool object by UUID: %s" % uuid)
        poolobj_uuid = conn.storagePoolLookupByUUID(uuid)
        if poolobj_uuid.name() == poolname:
            logger.info("pool object lookup by UUID succeed")
        else:
            logger.error("pool object lookup by UUID failed")
            retval += 1

        uuidstr = poolobj.UUIDString()
        logger.info("lookup the pool object by UUID string: %s" % uuidstr)
        poolobj_uuidstr = conn.storagePoolLookupByUUIDString(uuidstr)
        if poolobj_uuidstr.name() == poolname:
            logger.info("pool object lookup by UUID string succeed")
        else:
            logger.error("pool object lookup by UUID string failed")
            retval += 1

        if volname:
            logger.info("lookup volume object by volume name: %s" % volname)
            volobj = poolobj.storageVolLookupByName(volname)
            logger.info("lookup the pool object by volume object")
            poolobj_vol = volobj.storagePoolLookupByVolume()

            if poolobj_vol.name() == poolname:
                logger.info("pool object lookup by UUID string succeed")
            else:
                logger.error("pool object lookup by UUID string failed")
                retval += 1

    except libvirtError, e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    if retval:
        return 1

    return 0
