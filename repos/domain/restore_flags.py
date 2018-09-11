#!/usr/bin/env python

import time
import os
import libvirt
import functools

from libvirt import libvirtError
from src import sharedmod
from utils import utils
from xml.dom import minidom
from repos.domain.domain_common import get_flags, get_fileflags
from repos.domain.domain_common import check_fileflag, check_dom_state

try:
    import thread
except ImportError:
    import _thread as thread

required_params = ('guestname', 'flags',)
optional_params = {'dxml': 'alter',}

SAVE_PATH = "/tmp/%s.save"


def restore_flags(params):
    logger = params['logger']
    guestname = params['guestname']
    fileflags = []

    conn = sharedmod.libvirtobj['conn']
    domobj = conn.lookupByName(guestname)
    dxml = params.get('dxml', 'alter')

    flags = get_flags(params, logger)
    if flags == -1:
        return 1
    if flags == 0:
        logger.info("restore %s domain with no flag" % guestname)
    elif flags == 1:
        logger.info("restore %s domain with --bypass-cache" % guestname)
    elif flags == 2:
        logger.info("restore %s domain with --running" % guestname)
    elif flags == 3:
        logger.info("restore %s domain with --bypass-cache --running" % guestname)
    elif flags == 4:
        logger.info("restore %s domain with --paused" % guestname)
    elif flags == 5:
        logger.info("restore %s domain with --bypass-cache --paused" % guestname)

    if dxml == 'alter':
        # get guest xml
        guestxml = domobj.XMLDesc(0)
        # alter some portions of the domain XML
        dom = minidom.parseString(guestxml)
        tree_root = dom.documentElement
        boot_dev = tree_root.getElementsByTagName('boot')[0]
        boot_dev.setAttribute('dev', 'cdrom')
        dxml = tree_root.toprettyxml()
        logger.debug("minidom string is %s\n" % dxml)
    else:
        dxml = None

    save_path = SAVE_PATH % guestname
    if os.path.exists(save_path):
        os.remove(save_path)
    domobj.save(save_path)

    # If given flags include bypass-cache,check if bypass file system cache
    if flags % 2 == 1:
        logger.info("Given flags include --bypass-cache")
        # For restore, get file flag from /proc/PID/fdinfo/0
        thread.start_new_thread(get_fileflags, (save_path, fileflags, "0", logger,))

    # Guarantee get_fileflags shell has run before restore
    time.sleep(5)

    try:
        conn.restoreFlags(save_path, dxml, flags)
    except libvirtError as e:
        logger.info("restore domain failed" + str(e))
        return 1

    if flags % 2 == 1:
        if utils.isPower():
            com_flags = "0600000"
        else:
            com_flags = "0140000"
        if check_fileflag(fileflags[0], com_flags, logger):
            logger.info("Bypass file system cache successfully")
        else:
            logger.error("Bypass file system cache failed")
            return 1

    if flags & libvirt.VIR_DOMAIN_SAVE_PAUSED:
        state = libvirt.VIR_DOMAIN_PAUSED
    else:
        state = libvirt.VIR_DOMAIN_RUNNING
    ret = utils.wait_for(functools.partial(check_dom_state, domobj), 600)
    if ret != state:
        logger.error('The domain state is not as expected, state: %d' % state)
        return 1

    guestxml = domobj.XMLDesc(0)
    logger.debug("New guestxml is \n %s" % guestxml)

    if state == libvirt.VIR_DOMAIN_PAUSED:
        domobj.resume()

    dom = minidom.parseString(guestxml)
    tree_root = dom.documentElement
    new_boot_dev = tree_root.getElementsByTagName('boot')[0]
    if new_boot_dev.getAttribute('dev') != 'cdrom':
        logger.error("The domain is not changed as expected")
        return 1
    logger.info("The domain is changed as expected")
    logger.info("PASS")
    return 0


def restore_flags_clean(params):
    guestname = params['guestname']
    logger = params['logger']
    ret = utils.del_file(SAVE_PATH % guestname, logger)
