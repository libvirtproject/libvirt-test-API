#!/usr/bin/env python
# To test "virsh pool-uuid" command and related APIs
# To test 2 APIs in this case:
#    storagePoolLookupByUUID
#    storagePoolLookupByUUIDString

import os
import sys
import re
import time
import commands

import binascii
import libvirt

from xml.dom import minidom
from libvirt import libvirtError

from src import sharedmod

required_params = ('poolname',)
optional_params = {}

VIRSH_POOLUUID = "virsh pool-uuid"
POOLPATH = "/etc/libvirt/storage/"


def check_pool_uuid(poolname, UUIDString, logger):
    """ check UUID String of a pool """
    status, ret = commands.getstatusoutput(VIRSH_POOLUUID + ' %s' % poolname)
    if status:
        logger.error("executing " + "\"" + VIRSH_POOLUUID + ' %s' % poolname + "\"" + " failed")
        logger.error(ret)
        return False
    else:
        UUIDString_virsh = ret[:-1]
        logger.debug("UUIDString from API is %s" % UUIDString)
        logger.debug(
            "UUIDString from " +
            "\"" +
            VIRSH_POOLUUID +
            "\""
            " is %s" %
            UUIDString_virsh)
        if UUIDString_virsh == UUIDString:
            return True
        else:
            return False


def checking_uuid(logger, poolname, pooluuid):
    """check two uuid of pool which are from API and pool's XML"""
    global POOLPATH
    POOLPATH = POOLPATH + poolname + ".xml"
    xml = minidom.parse(POOLPATH)
    pool = xml.getElementsByTagName('pool')[0]
    uuid = pool.getElementsByTagName('uuid')[0].childNodes[0].data
    if uuid == pooluuid:
        return True
    else:
        return False


def pool_uuid(params):
    """ 1. call appropriate API to generate the UUIDStirng
        of a pool , then compared to the output of command
        virsh pool-uuid
        2. check 2 APIs in the case:
               storagePoolLookupByUUID
               storagePoolLookupByUUIDString
    """
    logger = params['logger']
    poolname = params['poolname']
    conn = sharedmod.libvirtobj['conn']

    pool_names = conn.listDefinedStoragePools()
    pool_names += conn.listStoragePools()

    if poolname in pool_names:
        poolobj = conn.storagePoolLookupByName(poolname)
    else:
        logger.error("%s not found\n" % poolname)
        return 1

    try:
        UUIDString = poolobj.UUIDString()
        logger.info(
            "the UUID string of pool %s is %s" %
            (poolname, UUIDString))

        # For a transient pool, set another path
        if not poolobj.isPersistent() == 1:
            logger.info("Can not check a transient pool by now.")
            return 0
        #allowing '-' and ' ' anywhere between character pairs,just check
        #one of them
        UUIDString1 = UUIDString.replace("-", " ")
        pool1 = conn.storagePoolLookupByUUIDString(UUIDString1)
        pool_name1 = pool1.name()
        logger.debug("The given UUID is \"%s\", the pool is \"%s\" using\
 storagePoolLookupByUUIDString" % (UUIDString1, pool_name1))

        UUIDString2 = UUIDString.replace("-", "")
        UUID_ascii = binascii.a2b_hex(UUIDString2)
        pool2 = conn.storagePoolLookupByUUID(UUID_ascii)
        pool_name2 = pool2.name()
        logger.debug("The given UUID is \"%s\", the pool is \"%s\" using \
storagePoolLookupByUUID" % (UUIDString2, pool_name2))

        if pool_name1 == pool_name2 and checking_uuid(logger, pool_name1, UUIDString):
            logger.info("Successed to get pool name \"%s\" using \"%s\""
                        % (pool_name1, UUIDString))

        if check_pool_uuid(poolname, UUIDString, logger):
            logger.info(VIRSH_POOLUUID + " test succeeded.")
            return 0
        else:
            logger.error(VIRSH_POOLUUID + " test failed.")
            return 1
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
