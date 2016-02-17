#!/usr/bin/env python

import os
import sys
import re
import time
import commands

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils
from repos.snapshot.common import check_domain_image

required_params = ('guestname',)
optional_params = {'snapshotname': '',
                   'xml': 'xmls/snapshot.xml',
                   }


def internal_create(params):
    """ create an internal snapshot for a given guest,
        this case could be with other cases togerther to
        check the functionality of snapshot
    """
    logger = params['logger']
    guestname = params['guestname']
    xmlstr = params['xml']

    if 'snapshotname' not in params:
        xmlstr = xmlstr.replace('SNAPSHOTNAME', str(int(time.time())))

    conn = sharedmod.libvirtobj['conn']
    guest_names = conn.listDefinedDomains()
    if guestname not in guest_names:
        logger.error("%s is not poweroff or doesn't exist" % guestname)
        return 1

    domobj = conn.lookupByName(guestname)

    logger.info("checking the format of its disk")
    if not check_domain_image(domobj, guestname, "qcow2", logger):
        logger.error("checking failed")
        return 1

    logger.debug("%s snapshot xml:\n%s" % (guestname, xmlstr))

    try:
        logger.info("create a snapshot for %s" % guestname)
        domobj.snapshotCreateXML(xmlstr, 0)
        logger.info("creating snapshot succeeded")
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
