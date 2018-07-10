#!/usr/bin/env python
# Test storagePoolLookupByTargetPath() API

import os

from libvirt import libvirtError
from src import sharedmod
from utils.utils import version_compare

required_params = ('poolname', 'targetpath',)
optional_params = {}


def pool_lookup_by_target_path(params):
    """
       Test API for storagePoolLookupByTargetPath in class virStoragePool
    """
    logger = params['logger']
    poolname = params['poolname']
    targetpath = params['targetpath']

    if not version_compare("libvirt-python", 4, 4, 0, logger):
        logger.info("Current libvirt-python don't support "
                    "storagePoolLookupByTargetPath().")
        return 0

    logger.info("pool name: %s" % poolname)
    logger.info("target path: %s" % targetpath)

    try:
        conn = sharedmod.libvirtobj['conn']
        pool = conn.storagePoolLookupByTargetPath(targetpath)
        pool_name_api = pool.name()
        logger.info("pool name api: %s" % pool_name_api)

        if not pool_name_api == poolname:
            logger.error("FAIL: pool name don't match, get pool fail")
            return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    logger.info("PASS: get pool by target path successful.")
    return 0
