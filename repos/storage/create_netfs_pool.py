#!/usr/bin/env python
# Create a netfs storage pool

import re

from libvirt import libvirtError
from src import sharedmod
from utils import xml_parser

required_params = ('poolname', 'sourcehost', 'sourcepath',)
optional_params = {'targetpath': '/mnt',
                   'xml': 'xmls/netfs_pool.xml',
                   }


def check_pool_create_libvirt(conn, poolname, logger):
    """Check the result of create storage pool inside libvirt """
    pool_names = conn.listStoragePools()
    logger.info("poolnames is: %s" % pool_names)
    # check thru libvirt that it's really created..
    try:
        pool_names.index(poolname)
    except ValueError:
        logger.info("check_pool_create %s storage pool pass" % poolname)
        return False
    # check
    return True


def check_pool_create_OS(conn, poolname, logger):
    """This function will check if the poolname mount location is really mounted
       by the OS or not. """
    # we need to get where libvirt thinks the poolname is mounted to...
    poolobj = conn.storagePoolLookupByName(poolname)
    poolxml = poolobj.XMLDesc(0)
    # parse the xml to see where this is mounted...
    out = xml_parser.xml_parser().parse(poolxml)
    dest_path = out["target"]["path"]
    src_host = out["source"]["host"]["attr"]["name"]
    src_path = out["source"]["dir"]["attr"]["path"]
    logger.info("src host: %s src path: %s tgt path: %s" %
                (src_host, src_path, dest_path))
    fd = open("/proc/mounts", "r")
    mount = src_host + ":" + src_path
    pat = mount + r"/*\s+" + dest_path
    found = 0
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
    logger.debug("current define storage pool: %s" % conn.listDefinedStoragePools())
    logger.debug("current active storage pool: %s" % conn.listStoragePools())


def create_netfs_pool(params):
    """ Create a network FS type storage pool from xml"""
    logger = params['logger']
    poolname = params['poolname']
    xmlstr = params['xml']

    conn = sharedmod.libvirtobj['conn']

    if check_pool_create_libvirt(conn, poolname, logger):
        logger.error("%s storage pool has already been created" % poolname)
        return 1

    logger.debug("storage pool xml:\n%s" % xmlstr)

    try:
        logger.info("Creating %s storage pool" % poolname)
        conn.storagePoolCreateXML(xmlstr, 0)
        display_pool_info(conn, logger)
        if check_pool_create_libvirt(conn, poolname, logger):
            logger.info("creating %s storage pool is \
                         successful in libvirt" % poolname)
            if check_pool_create_OS(conn, poolname, logger):
                logger.info("creating %s storage pool is SUCCESSFUL!!!" % poolname)
            else:
                logger.info("creating %s storage pool is \
                             UNSUCCESSFUL!!!" % poolname)
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
