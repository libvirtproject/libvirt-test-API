#!/usr/bin/env python

import libvirt
import lxml

from libvirt import libvirtError
from utils import utils

required_params = {'guestname', 'checkpoint_name'}
optional_params = {}


def checkpoint_get_parent(params):
    logger = params['logger']
    guestname = params['guestname']
    checkpoint_name = params.get('checkpoint_name', None)

    if not utils.version_compare('libvirt-python', 5, 6, 0, logger):
        logger.info("Current libvirt-python don't support getParent().")
        return 0

    logger.info("Checkpoint name: %s" % checkpoint_name)
    try:
        conn = libvirt.open()
        dom = conn.lookupByName(guestname)
        cp = dom.checkpointLookupByName(checkpoint_name)
        parent = cp.getParent()
        logger.info("Get parent by API: %s" % parent.getName())
        cp_xml = cp.getXMLDesc(libvirt.VIR_DOMAIN_CHECKPOINT_XML_NO_DOMAIN)
        if 'parent' in cp_xml:
            logger.info("checkpoint xml: %s" % cp_xml)
            tree = lxml.etree.fromstring(cp_xml)
            parent_name = tree.xpath("/domaincheckpoint/parent/name")[0].text
            if parent_name == parent.getName():
                logger.info("PASS: Check getParent() successful.")
            else:
                logger.error("FAIL: Check getParent() failed.")
                return 1
        else:
            logger.error("FAIL: no parent in %s." % checkpoint_name)
            return 1
    except libvirtError as err:
        logger.error("API error message: %s" % err.get_error_message())
        return 1

    return 0
