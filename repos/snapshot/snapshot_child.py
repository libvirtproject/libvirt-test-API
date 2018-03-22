#!/usr/bin/env python

import re
import time
import libvirt

from libvirt import libvirtError
from src import sharedmod
from utils import utils
from repos.snapshot.common import check_domain_image
from repos.snapshot.common import convert_flags

required_params = ('guestname', 'snapshotname', 'flags')
optional_params = {'children': ''}


FLAGDICT = {0: "", 1: " --descendants", 2: " --metadata", 4: " --leaves",
            8: " --no-leaves", 16: " --no-metadata", 32: " --inactive",
            64: " --active", 128: " --disk-only", 256: " --internal",
            512: " --external"}


def check_num_children(snap, children_num, flag, logger):
    if snap.numChildren(flag) != children_num:
        logger.error("snapshot's children number don't match")
        logger.error("Expect: %d" % children_num)
        logger.error("Got: %d" % snap.numChildren(flag))
        return False
    return True


def check_get_parent(child, parent, logger):
    if child.getParent().getXMLDesc() != parent.getXMLDesc():
        logger.error("Child snapshot's parent don't match, snapshot xml: %s" %
                     child.getXMLDesc())
        return False
    logger.info("Child-parent matches")
    return True


def snapshot_child(params):
    """ Check children list of given domain """

    logger = params['logger']
    flags = params['flags']
    guestname = params['guestname']
    snapshotname = params['snapshotname']
    children_name = params.get('children', '')

    children_name = [] if children_name == "" else children_name.split(",")

    conn = sharedmod.libvirtobj['conn']


    (flaglist, flagn) = convert_flags(flags, FLAGDICT, logger)

    logger.info("Flag list %s " % flaglist)
    logger.info("bitwise OR value of flags is %s" % flagn)

    try:
        domobj = conn.lookupByName(guestname)

        snapobj = domobj.snapshotLookupByName(snapshotname, 0)

        children = snapobj.listAllChildren(flagn)

        dom_children_name = [snap.getName() for snap in children]

        logger.info("Expect children list:" + str(children_name))
        logger.info("Got children list:" + str(dom_children_name))

        if set(dom_children_name) != set(children_name):
            return 1

        if not check_num_children(snapobj, len(children), flagn, logger):
            return 1

        if flagn | 1:
            # List children with flag "descendants", children's parent could be
            # a diffrent node.
            return 0

        for child in children:
            if not check_get_parent(child, snapobj, logger):
                return 1

    except libvirtError as e:
        logger.error("API error message: %s" % e.get_error_message())
        return 1

    return 0
