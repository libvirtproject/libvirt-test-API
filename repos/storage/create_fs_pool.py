#!/usr/bin/env python
# Create a storage pool of 'fs' type.

import re

from libvirt import libvirtError
from src import sharedmod
from utils import xml_parser

required_params = ('poolname', 'sourcepath',)
optional_params = {'sourceformat': 'ext3',
                   'targetpath': '/mnt',
                   'xml': 'xmls/fs_pool.xml',
                   }


def check_pool_create_libvirt(conn, poolname, logger):
    """Check the result of create storage pool on libvirt level.  """
    pool_names = conn.listStoragePools()
    logger.info("poolnames is: %s " % pool_names)
    # check thru libvirt that it's really created..
    if poolname in pool_names:
        return True
    else:
        logger.info("check_pool_create %s storage pool \
                     doesn't exist in libvirt!!!!" % poolname)
        return False


def check_pool_create_OS(poolobj, logger):
    """Check the result of create storage pool on OS level.  """
    poolxml = poolobj.XMLDesc(0)
    out = xml_parser.xml_parser().parse(poolxml)
    src_path = out["source"]["device"]["attr"]["path"]
    dest_path = out["target"]["path"]
    logger.info("src path: %s tgt path: %s" % (src_path, dest_path))
    pat = src_path + r"\s+" + dest_path
    found = 0
    fd = open("/proc/mounts", "r")
    for line in fd:
        if re.match(pat, line):
            found = 1
    fd.close()
    if found:
        return True
    else:
        return False


def display_pool_info(conn, logger):
    """Display current storage pool information"""
    logger.debug(
        "current define storage pool: %s" %
        conn.listDefinedStoragePools())
    logger.debug("current active storage pool: %s" % conn.listStoragePools())


def create_fs_pool(params):
    """ Create a fs type storage pool from xml"""
    logger = params['logger']
    poolname = params['poolname']
    xmlstr = params['xml']

    conn = sharedmod.libvirtobj['conn']

    pool_names = conn.listDefinedStoragePools()
    pool_names += conn.listStoragePools()

    if poolname in pool_names:
        logger.error("%s storage pool has already been created" % poolname)
        return 1

    logger.debug("storage pool xml:\n%s" % xmlstr)

    try:
        logger.info("Creating %s storage pool" % poolname)
        poolobj = conn.storagePoolCreateXML(xmlstr, 0)
        display_pool_info(conn, logger)
        if check_pool_create_libvirt(conn, poolname, logger):
            logger.info("creating %s storage pool is in libvirt" % poolname)
            if check_pool_create_OS(poolobj, logger):
                logger.info(
                    "creating %s storage pool is SUCCESSFUL!!!" %
                    poolname)
            else:
                logger.info("creating %s storage pool is UNSUCCESSFUL!!!" %
                            poolname)
                return 1
        else:
            logger.info("creating %s storage pool is \
                         UNSUCCESSFUL in libvirt!!!" % poolname)
            return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    return 0
