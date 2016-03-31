#!/usr/bin/env python

import os

from utils import utils
from src import sharedmod
from repos.storage import storage_common

required_params = ('poolname', 'sourcehost', 'sourcepath', 'diskpath', 'targetpath')
optional_params = {}


def storage_iscsi(params):
    """
    mount a iscsi.
    """
    logger = params['logger']
    poolname = params['poolname']
    sourcehost = params['sourcehost']
    sourcepath = params['sourcepath']
    targetpath = params['targetpath']

    # check pool exist
    conn = sharedmod.libvirtobj['conn']
    if not storage_common.check_pool(conn, poolname, logger):
        logger.debug("%s storage pool is defined" % poolname)

    # Prepare the disk
    disk_path = params.get("diskpath", "/dev/sdb1")
    if not os.path.exists(disk_path):
        if not storage_common.prepare_iscsi_disk(sourcehost, sourcepath, logger):
            logger.error("Failed to prepare iscsi disk")
            return 1
        if not utils.wait_for(lambda: os.path.exists(disk_path[:-1]), 5):
            logger.error("Target device didn't show up")
            return 1

    if not storage_common.prepare_partition(disk_path, logger):
        logger.error("Failed to prepare partition")
        return 1

    cmd = 'mkfs.ext3 -F %s' % disk_path
    ret, output = utils.exec_cmd(cmd, shell=True)
    logger.info("cmd: %s" % cmd)
    logger.debug("mkfs.ex3 output: %s" % output)

    if os.path.exists(targetpath):
        if os.path.isfile(targetpath):
            logger.debug("%s is file, remove it." % targetpath)
            os.remove(targetpath)
            os.mkdir(targetpath)
    else:
        os.mkdir(targetpath)

    cmd = 'mount %s %s' % (disk_path, targetpath)
    ret, output = utils.exec_cmd(cmd, shell=True)
    logger.info("cmd: %s" % cmd)
    logger.debug("mount output: %s" % output)

    return 0
