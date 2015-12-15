#!/usr/bin/env python
# To test "virsh domuuid" command

import os
import sys
import re
import commands

import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ()
optional_params = {}

VIRSH_DOMUUID = "virsh domuuid"


def check_domain_exists(conn, guestname, logger):
    """ check if the domain exists, may or may not be active """
    guest_names = []
    ids = conn.listDomainsID()
    for id in ids:
        obj = conn.lookupByID(id)
        guest_names.append(obj.name())

    guest_names += conn.listDefinedDomains()

    if guestname not in guest_names:
        logger.error("%s doesn't exist" % guestname)
        return False
    else:
        return True


def check_domain_uuid(guestname, UUIDString, logger):
    """ check UUID String of guest """
    status, ret = commands.getstatusoutput(VIRSH_DOMUUID + ' %s' % guestname)
    if status:
        logger.error("executing " + "\"" + VIRSH_DOMUUID + ' %s' % guestname + "\"" + " failed")
        logger.error(ret)
        return False
    else:
        UUIDString_virsh = ret[:-1]
        logger.debug("UUIDString from API is %s" % UUIDString)
        logger.debug("UUIDString from virsh domuuid is %s" % UUIDString_virsh)
        if UUIDString == ret[:-1]:
            return True
        else:
            return False


def domain_uuid(params):
    """check virsh domuuid command
    """
    logger = params['logger']
    guestname = params['guestname']
    logger.info("guest name is %s" % guestname)

    conn = sharedmod.libvirtobj['conn']

    if not check_domain_exists(conn, guestname, logger):
        logger.error("need a defined guest")
        return 1

    domobj = conn.lookupByName(guestname)

    try:
        logger.info("get the UUID string of %s" % guestname)
        UUIDString = domobj.UUIDString()
        if check_domain_uuid(guestname, UUIDString, logger):
            logger.info(
                "UUIDString from API is the same as the one from virsh")
            logger.info("UUID String is %s" % UUIDString)
            return 0
        else:
            logger.error(
                "UUIDString from API is not the same as the one from virsh")
            return 1
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
