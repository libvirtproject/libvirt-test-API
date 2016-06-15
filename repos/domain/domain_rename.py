#!/usr/bin/env python

import libvirt
import time
import threading
from libvirt import libvirtError

from repos.libvirtd.restart import restart
from src import sharedmod
from utils import utils

event_loop_thread = None
looping = True
rename_step = 0

required_params = ('guestname', )
optional_params = {'newname': '', 'negative': 'no'}


def event_loop_run():
    global looping
    while looping:
        libvirt.virEventRunDefaultImpl()
    return 0


def event_loop_stop(conn):
    """stop event thread and deregister domain callback function"""
    global looping
    global event_loop_thread
    looping = False
    conn.domainEventDeregister(rename_event_callback)
    event_loop_thread.join()


def event_loop_start():
    """start running default event handler implementation"""
    global event_loop_thread
    libvirt.virEventRegisterDefaultImpl()
    event_loop_run_arg = ()
    event_loop_thread = threading.Thread(target=event_loop_run, args=event_loop_run_arg,
                                         name="libvirtEventLoop")
    event_loop_thread.setDaemon(True)
    event_loop_thread.start()


def rename_event_callback(conn, domain, event, detail, opaque):
    """
    Domain renaming will undefine the domain first
    then redefine it with a new name.

    Check if everything is right with this callback.
    """

    global rename_step
    logger = opaque

    if event == libvirt.VIR_DOMAIN_EVENT_UNDEFINED:
        if detail == libvirt.VIR_DOMAIN_EVENT_UNDEFINED_RENAMED:
            logger.info("Domain undefined for rename")
            rename_step += 1

    if event == libvirt.VIR_DOMAIN_EVENT_DEFINED:
        if detail == libvirt.VIR_DOMAIN_EVENT_DEFINED_RENAMED:
            logger.info("Domain defined for rename")
            rename_step *= 2


def domain_rename(params):
    """Rename a domain
    """
    domname = params['guestname']
    logger = params['logger']
    negative = params.get('negative', 'no')
    newname = params.get('newname', None)
    logger.info("renaming domain '%s' to '%s'" % (domname, newname))

    # Use event loop to detect rename events
    rename_step = 0
    event_loop_start()
    conn = libvirt.open(None)
    conn.domainEventRegister(rename_event_callback, logger)

    try:
        # Rename domain
        domobj = conn.lookupByName(domname)
        domobj.rename(newname, 0)
        time.sleep(3)
        event_loop_stop(conn)

    except libvirtError, e:
        if negative == 'no':
            logger.error("API error message: %s, error code is %s"
                         % (e.message, e.get_error_code()))
            logger.error("rename failed")
            return 1
        else:
            logger.info("Got exception as expected.")
            return 0

    if negative == 'yes':
        logger.error("Negative test failed")
        return 1

    if rename_step != 2:
        logger.error("Didn't get expected events.")
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
