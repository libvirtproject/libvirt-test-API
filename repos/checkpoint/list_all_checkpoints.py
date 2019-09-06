#!/usr/bin/env python

import libvirt
import os

from libvirt import libvirtError
from utils import utils

required_params = {'guestname'}
optional_params = {'flags': None}


def check_checkpoint_list(guestname, name_list, logger):
    checkpoint_xml_path = "/var/lib/libvirt/qemu/checkpoint/%s/" % guestname
    cp_list = []
    for root, dirs, files in os.walk(checkpoint_xml_path):
        for file_name in files:
            cp_list.append(file_name.replace('.xml', ''))
    logger.info("Checkpoint list in path: %s" % cp_list)
    name_list.sort()
    cp_list.sort()
    if name_list == cp_list:
        return 0
    else:
        return 1


def check_checkpoint_list_roots(guestname, dom, name_list, logger):
    roots_list = []
    cp_lists = dom.listAllCheckpoints()
    for cp_list in cp_lists:
        cp_xml = cp_list.getXMLDesc(libvirt.VIR_DOMAIN_CHECKPOINT_XML_NO_DOMAIN)
        if "<parent>" not in cp_xml:
            roots_list.append(cp_list.getName())
    roots_list.sort()
    name_list.sort()
    logger.info("Check checkpoint list with roots.")
    if roots_list == name_list:
        return 0
    else:
        return 1


def check_checkpoint_list_topological(guestname, dom, name_list, logger):
    topological_list = []
    cp_lists = dom.listAllCheckpoints()
    logger.info("Check checkpoint list with topological.")
    # TODO
    return 0


def check_checkpoint_list_leaves(guestname, dom, name_list, logger):
    leaves_list = []
    cp_lists = dom.listAllCheckpoints()
    logger.info("Check checkpoint list with leaves.")
    # TODO
    return 0


def check_checkpoint_list_no_leaves(guestname, dom, name_list, logger):
    logger.info("Check checkpoint list with no leaves.")
    # TODO
    return 0


def list_all_checkpoints(params):
    logger = params['logger']
    guestname = params['guestname']
    flag = utils.parse_flags(params)

    if not utils.version_compare('libvirt-python', 5, 6, 0, logger):
        logger.info("Current libvirt-python don't support listAllCheckpoints().")
        return 0
    logger.info("flag: %s" % flag)

    try:
        conn = libvirt.open()
        dom = conn.lookupByName(guestname)
        cp_lists = dom.listAllCheckpoints(flag)
        name_list = []
        for cp in cp_lists:
            name_list.append(cp.getName())
        logger.info("Get checkpoint list from API: %s" % name_list)
    except libvirtError as err:
        logger.error("API error message: %s" % err.get_error_message())
        return 1

    if (flag == libvirt.VIR_DOMAIN_CHECKPOINT_LIST_ROOTS or
            flag == libvirt.VIR_DOMAIN_CHECKPOINT_LIST_DESCENDANTS):
        check_result = check_checkpoint_list_roots(guestname, dom, name_list, logger)
    elif flag == libvirt.VIR_DOMAIN_CHECKPOINT_LIST_TOPOLOGICAL:
        check_result = check_checkpoint_list_topological(guestname, dom, name_list, logger)
    elif flag == libvirt.VIR_DOMAIN_CHECKPOINT_LIST_LEAVES:
        check_result = check_checkpoint_list_leaves(guestname, dom, name_list, logger)
    elif flag == libvirt.VIR_DOMAIN_CHECKPOINT_LIST_NO_LEAVES:
        check_result = check_checkpoint_list_no_leaves(guestname, dom, name_list, logger)
    else:
        check_result = check_checkpoint_list(guestname, name_list, logger)

    if check_result:
        logger.error("FAIL: get all checkpoints failed.")
        return 1
    else:
        logger.info("PASS: get all checkpoints successful.")
    return 0
