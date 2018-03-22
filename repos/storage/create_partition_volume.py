#!/usr/bin/env python
# Create volume for storage pool of partition type

from libvirt import libvirtError
from src import sharedmod
from utils import process

required_params = ('poolname', 'volname', 'volformat', 'capacity',)
optional_params = {}


def partition_volume_check(poolobj, volname):
    """check the new created volume, the way of checking is to get
       the path of the newly created volume, then grep /proc/partitions
       to find out the new partition in that. """

    volobj = poolobj.storageVolLookupByName(volname)
    volpath = volobj.path()
    logger.debug("the path of volume is %s" % volpath)

    partition_name = volpath.split("/")[-1]
    shell_cmd = "grep %s /proc/partitions" % partition_name
    logger.debug("excute the shell command %s to \
                  check the newly created partition" % shell_cmd)
    ret = process.run(shell_cmd, shell=True, ignore_status=True)
    if ret.exit_status == 0 and volname in poolobj.listVolumes():
        return 0
    else:
        return 1


def virsh_vol_list(poolname):
    """using virsh command list the volume information"""

    shell_cmd = "virsh vol-list %s" % poolname
    ret = process.run(shell_cmd, shell=True, ignore_status=True)
    logger.debug(ret.stdout)


def create_partition_volume(params):
    """create a volume in the disk type of pool"""

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

    xmlstr = xmlstr.replace('SUFFIX', capacity[-1])
    xmlstr = xmlstr.replace('CAP', capacity[:-1])

    logger.info("before create the new volume, \
                 current volume list is %s" %
                poolobj.listVolumes())

    logger.info("and using virsh command to \
                 ouput the volume information in the pool %s" % poolname)
    virsh_vol_list(poolname)

    logger.debug("volume xml:\n%s" % xmlstr)

    try:
        logger.info("create %s volume" % volname)
        poolobj.createXML(xmlstr, 0)
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    logger.info("volume create successfully, and output the volume information")
    virsh_vol_list(poolname)

    logger.info("Now, check the validation of the created volume")
    check_res = partition_volume_check(poolobj, volname)

    if not check_res:
        logger.info("checking succeed")
        return 0
    else:
        logger.error("checking failed")
        return 1
