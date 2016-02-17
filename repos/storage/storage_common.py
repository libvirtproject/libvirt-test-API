#!/usr/bin/env python

import os
import re
import sys

import libvirt
from libvirt import libvirtError

from src import sharedmod


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
