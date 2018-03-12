#!/usr/bin/env python
# To test "virsh domname" command

import os
import sys
import re

from utils import process

required_params = ()
optional_params = {}

VIRSH_DOMNAME = "virsh domname"
VIRSH_IDS = "virsh --quiet list |awk '{print $1}'"
VIRSH_DOMS = "virsh --quiet list |awk '{print $2}'"


def get_output(logger, command):
    """execute shell command
    """
    ret = process.run(command, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("executing " + "\"" + command + "\"" + " failed")
        logger.error(ret.stdout)
    return ret.exit_status, ret.stdout


def domain_name(params):
    """check virsh domname command
    """
    logger = params['logger']

    ids = []
    if 'domainid' in params:
        ids.append(params['domainid'])
    else:
        status, id_ret = get_output(logger, VIRSH_IDS)
        if not status:
            ids = id_ret.split('\n')
        else:
            return 1

    status, ids_ret = get_output(logger, VIRSH_IDS)
    if not status:
        ids_list = ids_ret.split('\n')
    else:
        return 1

    status, doms_ret = get_output(logger, VIRSH_DOMS)
    if not status:
        doms_list = doms_ret.split('\n')
    else:
        return 1

    id_domname = {}
    for id in ids_list:
        index = ids_list.index(id)
        id_domname[id] = doms_list[index]

    for id in ids:
        status, domname_ret = get_output(logger, VIRSH_DOMNAME + " %s" % id)
        if status:
            return 1
        domname = domname_ret[:-1]
        if id_domname[id] == domname:
            logger.info("domid %s corresponds to guest %s" % (id, domname))
        else:
            logger.error("domid %s fails to match to guest %s" % (id, domname))
            return 1

    return 0
