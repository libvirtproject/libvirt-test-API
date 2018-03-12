#!/usr/bin/env python
# storage pool volume lookup testing

from libvirt import libvirtError
from src import sharedmod

required_params = ('poolname', 'volname',)
optional_params = {
}


def vol_lookup(params):
    """storage pool volume lookup testing"""

    global logger
    logger = params['logger']
    poolname = params['poolname']
    volname = params['volname']
    retval = 0

    logger.info("the poolname is %s" % poolname)
    logger.info("the given volume name is %s" % volname)

    conn = sharedmod.libvirtobj['conn']
    try:
        poolobj = conn.storagePoolLookupByName(poolname)

        logger.info("lookup the volume object by name: %s" % volname)
        volobj = poolobj.storageVolLookupByName(volname)
        if volobj.name() == volname:
            logger.info("volume object lookup by name succeed")
        else:
            logger.error("volume object lookup by name failed")
            retval += 1

        volkey = volobj.key()
        logger.info("lookup the volume object by key: %s" % volkey)
        volobj_key = conn.storageVolLookupByKey(volkey)
        if volobj_key.name() == volname:
            logger.info("volume object lookup by key succeed")
        else:
            logger.error("volume object lookup by key failed")
            retval += 1

        volpath = volobj.path()
        logger.info("lookup the volume object by path: %s" % volpath)
        volobj_path = conn.storageVolLookupByPath(volpath)
        if volobj_path.name() == volname:
            logger.info("volume object lookup by path succeed")
        else:
            logger.error("volume object lookup by path failed")
            retval += 1

    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    if retval:
        return 1

    return 0
