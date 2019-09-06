#!/usr/bin/env python

import libvirt
import re

from libvirt import libvirtError
from utils import utils

required_params = {'guestname', 'checkpoint_name'}
optional_params = {'flags': None}


def checkpoint_get_xml(params):
    logger = params['logger']
    guestname = params['guestname']
    checkpoint_name = params.get('checkpoint_name', None)
    flag = utils.parse_flags(params)

    if not utils.version_compare('libvirt-python', 5, 6, 0, logger):
        logger.info("Current libvirt-python don't support getXMLDesc().")
        return 0

    logger.info("Checkpoint name: %s" % checkpoint_name)
    logger.info("flag: %s" % flag)
    if flag == libvirt.VIR_DOMAIN_CHECKPOINT_XML_SIZE:
        logger.info("Bug 1207659: Don't support this flag.")
        return 0

    try:
        conn = libvirt.open()
        dom = conn.lookupByName(guestname)
        cp = dom.checkpointLookupByName(checkpoint_name)
        cp_xml = cp.getXMLDesc(flag)
    except libvirtError as err:
        logger.error("API error message: %s" % err.get_error_message())
        return 1

    checkpoint_xml_path = "/var/lib/libvirt/qemu/checkpoint/%s/%s.xml" % (guestname, checkpoint_name)
    cp_fd = open(checkpoint_xml_path, 'r')
    checkpoint_xml = cp_fd.read()
    checkpoint_xml = re.sub(r'<!--\n.*\n-->\n\n', '', checkpoint_xml, flags=re.S)
    if flag == libvirt.VIR_DOMAIN_CHECKPOINT_XML_NO_DOMAIN:
        cp_xml = cp_xml.replace('</domaincheckpoint>\n', '')
        if cp_xml in checkpoint_xml:
            logger.info("PASS: check checkpoint xml successful.")
        else:
            logger.error("FAIL: check checkpoint xml failed.")
            return 1
    elif flag == libvirt.VIR_DOMAIN_CHECKPOINT_XML_SIZE:
        logger.info("Don't support this flag.")
    elif flag == libvirt.VIR_DOMAIN_CHECKPOINT_XML_SECURE or flag == 0:
        if cp_xml == checkpoint_xml:
            logger.info("PASS: check checkpoint xml successful.")
        else:
            logger.error("FAIL: check checkpoint xml failed.")
            return 1

    return 0
