#!/usr/bin/env python

import libvirt
import time
import threading
from libvirt import libvirtError

from repos.libvirtd.restart import restart
from src import sharedmod
from utils import utils

required_params = ('guestname', )
optional_params = {'newname': '', 'negative': 'no'}


def domain_rename(params):
    """Rename a domain
    """
    domname = params['guestname']
    logger = params['logger']
    negative = params.get('negative', 'no')
    newname = params.get('newname', None)
    logger.info("renaming domain '%s' to '%s'" % (domname, newname))

    conn = libvirt.open(None)

    try:
        # Rename domain
        domobj = conn.lookupByName(domname)
        domobj.rename(newname, 0)
        time.sleep(3)

    except libvirtError as e:
        if negative == 'no':
            logger.error("API error message: %s, error code is %s"
                         % (e.get_error_message(), e.get_error_code()))
            logger.error("rename failed")
            return 1
        else:
            logger.info("Got exception as expected.")
            return 0

    if negative == 'yes':
        logger.error("Negative test failed")
        return 1

    logger.info("domain renamed.")

    return 0

def domain_rename_clean(params):
    logger = params['logger']
    ret_flag = params.get('ret_flag')
    conn = sharedmod.libvirtobj['conn']

    logger.info("test returned %s" % str(ret_flag))

    if ret_flag:
        logger.info("test failed, restart libvirtd service:")
        if restart({'logger': logger}):
            return 1
        # Sleep 3s, restart libvirtd too often will make systemd consider libvirtd failed.
        time.sleep(3)
        sharedmod.libvirtobj['conn'] = libvirt.open()

    return 0
