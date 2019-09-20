#!/usr/bin/env python
# List all storage pool

import libvirt

from libvirt import libvirtError
from utils import utils

required_params = ()
optional_params = {'flags': None}


def check_iscsi_direct_pool(pool_list, logger):
    pool_num = 0
    for pool in pool_list:
        pool_xml = pool.XMLDesc()
        if "pool type='iscsi-direct'" in pool_xml:
            pool_num += 1
    if pool_num == len(pool_list):
        return True
    else:
        return False


def pool_list(params):
    """ List all storage pool """

    logger = params['logger']
    flag = utils.parse_flags(params)

    if flag == libvirt.VIR_CONNECT_LIST_STORAGE_POOLS_ISCSI_DIRECT:
        if not utils.version_compare('libvirt-python', 5, 6, 0, logger):
            logger.info("Current libvirt-python don't support VIR_CONNECT_LIST_STORAGE_POOLS_ISCSI_DIRECT.")
            return 0
    try:
        conn = libvirt.open()
        pool_list = conn.listAllStoragePools(flag)
        logger.info("Pool list: %s" % pool_list)
    except libvirtError as err:
        logger.error("libvirt call failed: " + err.get_error_message())
        return 1

    if flag == libvirt.VIR_CONNECT_LIST_STORAGE_POOLS_ISCSI_DIRECT:
        ret = check_iscsi_direct_pool(pool_list, logger)
    if not ret:
        logger.error("FAIL: list storage pool failed.")
        return 1

    logger.info("PASS: list storage pool succeed.")
    return 0
