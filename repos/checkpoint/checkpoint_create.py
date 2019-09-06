#!/usr/bin/env python

import libvirt
import os
import datetime

from libvirt import libvirtError
from utils import utils

required_params = {'guestname'}
optional_params = {'xml': 'xmls/checkpoint.xml',
                   'checkpoint_name': None,
                   'redefine_name': None,
                   'flags': None}


def checkpoint_create(params):
    logger = params['logger']
    guestname = params['guestname']
    domxml = params.get('xml', None)
    checkpoint_name = params.get('checkpoint_name', None)
    redefine_name = params.get('redefine_name', None)
    flag = utils.parse_flags(params)

    if not utils.version_compare('libvirt-python', 5, 6, 0, logger):
        logger.info("Current libvirt-python don't support checkpointCreateXML().")
        return 0

    logger.info("Checkpoint name: %s" % checkpoint_name)
    logger.info("Redefine checkpoint name: %s" % redefine_name)
    logger.info("flag: %s" % flag)
    if flag != libvirt.VIR_DOMAIN_CHECKPOINT_CREATE_REDEFINE:
        if checkpoint_name is None:
            domxml = domxml.replace('<name></name>\n', '')
        else:
            domxml = domxml.replace('CHECKPOINT_NAME', checkpoint_name)
    logger.info("Domain checkpoint xml: %s" % domxml)

    try:
        conn = libvirt.open()
        dom = conn.lookupByName(guestname)
        cp_lists = dom.listAllCheckpoints()
        for cp in cp_lists:
            if cp.getName() == checkpoint_name:
                cp.delete()
            elif cp.getName() == redefine_name:
                cp.delete(libvirt.VIR_DOMAIN_CHECKPOINT_DELETE_METADATA_ONLY)
        current_time = int(datetime.datetime.now().timestamp())
        logger.info("Current time: %s" % current_time)
        dom.checkpointCreateXML(domxml, flag)
    except libvirtError as err:
        logger.error("API error message: %s" % err.get_error_message())
        return 1

    checkpoint_xml_path = ""
    if flag != libvirt.VIR_DOMAIN_CHECKPOINT_CREATE_REDEFINE:
        if checkpoint_name is None:
            checkpoint_xml_path = "/var/lib/libvirt/qemu/checkpoint/%s/%s.xml" % (guestname, current_time)
        else:
            checkpoint_xml_path = "/var/lib/libvirt/qemu/checkpoint/%s/%s.xml" % (guestname, checkpoint_name)
    else:
        checkpoint_xml_path = "/var/lib/libvirt/qemu/checkpoint/%s/%s.xml" % (guestname, redefine_name)
    if not os.path.exists(checkpoint_xml_path):
        logger.error("FAIL: checkpoint xml path don't exist.")
        return 1

    cp_lists = dom.listAllCheckpoints()
    for cp in cp_lists:
        cp_name = cp.getName()
        if checkpoint_name:
            if cp_name == checkpoint_name:
                logger.info("PASS: check checkpoint name successful.")
                return 0
        elif redefine_name:
            if cp_name == redefine_name:
                logger.info("PASS: check checkpoint redefine successful.")
                return 0
        else:
            if cp_name == str(current_time):
                logger.info("PASS: check checkpoint name successful.")
                return 0
    logger.error("FAIL: check checkpoint name failed.")
    return 1


def checkpoint_create_clean(params):
    logger = params['logger']
    guestname = params['guestname']
    try:
        conn = libvirt.open()
        dom_list = conn.listAllDomains()
        if len(dom_list) > 0:
            dom = conn.lookupByName(guestname)
            cp_lists = dom.listAllCheckpoints()
            for cp in cp_lists:
                cp.delete(libvirt.VIR_DOMAIN_CHECKPOINT_DELETE_CHILDREN |
                          libvirt.VIR_DOMAIN_CHECKPOINT_DELETE_METADATA_ONLY)
    except libvirtError as err:
        logger.error("Clean all checkpoint fail: %s" % err.get_error_message())
