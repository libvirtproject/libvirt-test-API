#!/usr/bin/env python
# Define storage pool of 'dir' type

import os
import re
import sys
import commands

import libvirt
from libvirt import libvirtError

from src import sharedmod
from repos.storage import storage_common

VIRSH_POOLLIST = "virsh --quiet pool-list --all|awk '{print $1}'|grep \"^%s$\""
POOL_STAT = "virsh --quiet pool-list --all|grep \"^%s\\b\" |grep \"inactive\""
POOL_DESTROY = "virsh pool-destroy %s"
POOL_UNDEFINE = "virsh pool-undefine %s"

required_params = ('poolname',)
optional_params = {'targetpath': '/var/lib/libvirt/images/dirpool',
                   'xml': 'xmls/dir_pool.xml',
                   }


def define_dir_pool(params):
    """Define a dir type storage pool from xml"""
    logger = params['logger']
    poolname = params['poolname']
    xmlstr = params['xml']

    conn = sharedmod.libvirtobj['conn']

    if not storage_common.check_pool(conn, poolname, logger):
        logger.error("%s storage pool is defined" % poolname)
        return 1

    targetpath = params.get('targetpath', '/var/lib/libvirt/images/dirpool')
    if not os.path.exists(targetpath):
        os.mkdir(targetpath)

    logger.debug("storage pool xml:\n%s" % xmlstr)

    pool_num1 = conn.numOfDefinedStoragePools()
    logger.info("original storage pool define number: %s" % pool_num1)
    storage_common.display_pool_info(conn, logger)

    try:
        logger.info("define %s storage pool" % poolname)
        conn.storagePoolDefineXML(xmlstr, 0)
        pool_num2 = conn.numOfDefinedStoragePools()
        logger.info("current storage pool define number: %s" % pool_num2)
        storage_common.display_pool_info(conn, logger)
        if storage_common.check_pool_define(poolname, logger) and pool_num2 > pool_num1:
            logger.info("define %s storage pool is successful" % poolname)
        else:
            logger.error("%s storage pool is undefined" % poolname)
            return 1
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0


def define_dir_pool_clean(params):
    logger = params['logger']
    poolname = params['poolname']
    (status, output) = commands.getstatusoutput(VIRSH_POOLLIST % poolname)
    if not status:
        logger.info("remove storage pool %s" % poolname)
        (status, output) = commands.getstatusoutput(POOL_STAT % poolname)
        if status:
            (status, output) = commands.getstatusoutput(POOL_DESTROY % poolname)
            if status:
                logger.error("failed to destroy storage pool %s" % poolname)
                logger.error("%s" % output)
            else:
                (status, output) = commands.getstatusoutput(POOL_UNDEFINE % poolname)
                if status:
                    logger.error("failed to undefine storage pool %s" % poolname)
                    logger.error("%s" % output)
        else:
            (status, output) = commands.getstatusoutput(POOL_UNDEFINE % poolname)
            if status:
                logger.error("failed to undefine storage pool %s" % poolname)
                logger.error("%s" % output)
