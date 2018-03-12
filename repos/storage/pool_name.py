#!/usr/bin/env python

from libvirt import libvirtError
from src import sharedmod
from utils import process

required_params = ('poolname',)
optional_params = {}

VIRSH_POOLNAME = "virsh pool-name"


def check_pool_uuid(poolname, UUIDString, logger):
    """ check the output of virsh pool-name """
    cmd = VIRSH_POOLNAME + ' %s' % UUIDString
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("executing " + "\"" + VIRSH_POOLNAME + ' %s' % UUIDString + "\"" + " failed")
        logger.error(ret.stdout)
        return False
    else:
        poolname_virsh = ret.stdout[:-1]
        logger.debug("poolname from " + VIRSH_POOLNAME + " is %s" % poolname_virsh)
        logger.debug("poolname we expected is %s" % poolname)
        if poolname_virsh == poolname:
            return True
        else:
            return False


def pool_name(params):
    """ get the UUIDString of a pool, then call
        virsh pool-name to generate the name of pool,
        then check it
    """
    logger = params['logger']
    poolname = params['poolname']
    conn = sharedmod.libvirtobj['conn']

    pool_names = conn.listDefinedStoragePools()
    pool_names += conn.listStoragePools()

    if poolname in pool_names:
        poolobj = conn.storagePoolLookupByName(poolname)
    else:
        logger.error("%s not found\n" % poolname)
        return 1

    try:
        UUIDString = poolobj.UUIDString()
        logger.info(
            "the UUID string of pool %s is %s" %
            (poolname, UUIDString))
        if check_pool_uuid(poolname, UUIDString, logger):
            logger.info(VIRSH_POOLNAME + " test succeeded.")
        else:
            logger.error(VIRSH_POOLNAME + " test failed.")
            return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
