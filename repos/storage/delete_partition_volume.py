#!/usr/bin/env python

from libvirt import libvirtError
from src import sharedmod
from utils import process

required_params = ('poolname', 'volname',)
optional_params = {}


def partition_volume_check(poolobj, volname, partition_name):
    """check the newly deleted volume, the way of checking is to
       grep the partition name of the volume in /proc/partitions
       to ensure its non-existence"""

    shell_cmd = "grep %s /proc/partitions" % partition_name
    logger.debug("excute the shell command %s to \
                  check the newly created partition" % shell_cmd)
    ret = process.run(shell_cmd, shell=True, ignore_status=True)
    if ret.exit_status != 0 and volname not in poolobj.listVolumes():
        return 0
    else:
        return 1


def virsh_vol_list(poolname):
    """using virsh command list the volume information"""

    shell_cmd = "virsh vol-list %s" % poolname
    out = process.system_output(shell_cmd, shell=True, ignore_status=True)
    logger.debug(out)


def delete_partition_volume(params):
    """delete a volume in the disk type of pool"""

    global logger
    logger = params['logger']
    params.pop('logger')
    poolname = params.pop('poolname')
    volname = params['volname']

    logger.info("the poolname is %s, volname is %s" % (poolname, volname))

    conn = sharedmod.libvirtobj['conn']

    storage_pool_list = conn.listStoragePools()

    if poolname not in storage_pool_list:
        logger.error("pool %s doesn't exist or not running")
        return 1

    poolobj = conn.storagePoolLookupByName(poolname)

    logger.info("before deleting a volume, \
                 current volume list in the pool %s is %s" %
                (poolname, poolobj.listVolumes()))

    logger.info("and using virsh command to \
                 ouput the volume information in the pool %s" % poolname)
    virsh_vol_list(poolname)

    volobj = poolobj.storageVolLookupByName(volname)
    volpath = volobj.path()
    logger.debug("the path of volume is %s" % volpath)

    partition_name = volpath.split("/")[-1]

    try:
        logger.info("delete volume %s" % volname)
        volobj.delete(0)
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    logger.info("delete volume successfully, and output the volume information")
    logger.info("after deleting a volume, \
                 current volume list in the pool %s is %s" %
                (poolname, poolobj.listVolumes()))
    virsh_vol_list(poolname)

    logger.info("Now, check the validation of deleting volume")
    check_res = partition_volume_check(poolobj,
                                       volname, partition_name)

    if not check_res:
        logger.info("checking succeed")
        return 0
    else:
        logger.error("checking failed")
        return 1
