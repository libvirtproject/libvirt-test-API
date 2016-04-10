#!/usr/bin/env python

import os
import time

from utils import utils


def display_pool_info(conn, logger):
    """Display current storage pool information"""
    logger.debug("current define storage pool: %s" % conn.listDefinedStoragePools())
    logger.debug("current active storage pool: %s" % conn.listStoragePools())


def check_pool(conn, poolname, logger):
    path = "/etc/libvirt/storage/%s.xml" % poolname
    logger.debug("%s xml file path: %s" % (poolname, path))

    if os.access(path, os.R_OK):
        logger.debug("Check: %s does exist." % path)
        try:
            poolobj = conn.storagePoolLookupByName(poolname)
            if poolobj.isActive():
                poolobj.destroy()

            poolobj.undefine()
            logger.debug("Undefine %s successful." % poolname)
        except ValueError:
            logger.debug("Undefine %s failed." % poolname)
            return False

    return True


def check_pool_define(poolname, logger):
    """Check define storage pool result, if define storage is successful,
       poolname.xml will exist under /etc/libvirt/storage/
       and can use virt-xml-validate tool to check the file validity
    """
    path = "/etc/libvirt/storage/%s.xml" % poolname
    logger.debug("%s xml file path: %s" % (poolname, path))
    if os.access(path, os.R_OK):
        return True
    else:
        return False


def prepare_iscsi_disk(portal, wwn, logger):
    """
    Discover and login the iscsi disk, and make fs on it.
    """
    dic_cmd = ("iscsiadm --mode discoverydb --type sendtargets"
               " --portal %s --discover" % portal)
    ret, output = utils.exec_cmd(dic_cmd, shell=True)
    logger.debug("discovery output: %s" % output)
    log_cmd = ("iscsiadm --mode node --targetname %s --portal %s"
               " --login" % (wwn, portal))
    ret, output = utils.exec_cmd(log_cmd, shell=True)
    logger.debug("login output: %s" % output)
    if ret:
        return False
    else:
        return True


def prepare_partition(path, logger):
    timeout = 5
    dev, num = path[:-1], path[-1]
    fdisk_cmd = ("sync && echo -e 'o\\nn\\np\\n%d\\n\\n\\nw\\n'"
                 "|fdisk %s" % (int(num), dev))
    ret, output = utils.exec_cmd(fdisk_cmd, shell=True)
    logger.debug("fdisk output: %s" % output)

    while timeout > 0:
        if os.path.exists(path):
            utils.exec_cmd("dd if=/dev/zero of=%s bs=512 count=1000; sync"
                           % path, shell=True)
            return True
        utils.exec_cmd("partprobe %s" % dev, shell=True)
        time.sleep(1)
        timeout = timeout - 1

    return False
