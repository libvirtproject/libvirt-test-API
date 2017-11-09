#!/usr/bin/env python
# For testing domain events with pure python event loop which using implement in
# sample event-tests from libvirt-python. Also the using domainEventRegisterAny
# for callback.
#
#
#################################################################################
# Start off by implementing a general purpose event loop for anyones use
#################################################################################

import libvirt
import time

from libvirt import libvirtError
from utils.events import eventLoopPure
from utils.utils import version_compare

STATE = None

required_params = ('guestname',)
optional_params = {}


##########################################################################
# Everything that now follows is a simple demo of domain lifecycle events
##########################################################################
def eventToString(event):
    eventStrings = ("Defined",
                    "Undefined",
                    "Started",
                    "Suspended",
                    "Resumed",
                    "Stopped",
                    "Shutdown",
                    "PMSuspended")
    return eventStrings[event]


def detailToString(event, detail):
    eventStrings = (
        ("Added", "Updated", "Renamed", "Snapshot"),
        ("Removed", "Renamed"),
        ("Booted", "Migrated", "Restored", "Snapshot", "Wakeup"),
        ("Paused", "Migrated", "IOError", "Watchdog", "Restored", "Snapshot"),
        ("Unpaused", "Migrated", "Snapshot"),
        ("Shutdown", "Destroyed", "Crashed", "Migrated", "Saved", "Failed",
         "Snapshot"),
        ("Finished", "Finished after guest request", "Finished after host request"),
        ("Memory", "Disk")
    )
    return eventStrings[event][detail]


def myDomainEventCallback(conn, dom, event, detail, opaque):
    global STATE
    logger = opaque
    logger.debug("myDomainEventCallback EVENT: Domain %s(%s) %s %s" %
                 (dom.name(), dom.ID(), eventToString(event),
                  detailToString(event, detail)))
    STATE = eventToString(event)


def check_domain_running(conn, guestname, logger):
    """ check if the domain exists, may or may not be active """
    guest_names = []
    ids = conn.listDomainsID()
    for id in ids:
        obj = conn.lookupByID(id)
        guest_names.append(obj.name())

    if guestname not in guest_names:
        logger.error("%s doesn't exist or not running" % guestname)
        return 1
    else:
        return 0


def shutdown_event(domobj, guestname, timeout, logger):
    """shutdown the guest, then check the event infomation"""
    global STATE
    STATE = None
    logger.info("power off %s" % guestname)
    try:
        domobj.shutdown()
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        logger.error("Error: fail to power off %s" % guestname)
        return 1

    while timeout:
        if STATE == "Stopped":
            logger.info("The event is Stopped, PASS")
            break
        elif STATE is not None:
            logger.debug("The event is %s", STATE)
        else:
            timeout -= 5
            time.sleep(5)

    if timeout <= 0:
        logger.error("Timeout! The event is %s" % STATE)
        return 1

    return 0


def bootup_event(domobj, guestname, timeout, logger):
    """bootup the guest, then check the event infomation"""
    global STATE
    STATE = None
    logger.info("boot up guest %s" % guestname)
    try:
        domobj.create()
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        logger.error("Error: fail to bootup %s " % guestname)
        return 1

    while timeout:
        if STATE == "Started":
            logger.info("The event is Started, PASS")
            break
        elif STATE is not None:
            logger.error("The event is %s", STATE)
        else:
            timeout -= 5
            time.sleep(5)

    if timeout <= 0:
        logger.error("Timeout! The event is %s" % STATE)
        return 1

    return 0


def suspend_event(domobj, guestname, timeout, logger):
    """suspend the guest, then check the event infomation"""
    global STATE
    STATE = None
    logger.info("suspend guest %s" % guestname)
    try:
        domobj.suspend()
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        logger.error("Error: fail to suspend %s" % guestname)
        return 1

    while timeout:
        if STATE == "Suspended":
            logger.info("The event is Suspended, PASS")
            break
        elif STATE is not None:
            logger.error("The event is %s", STATE)
        else:
            timeout -= 5
            time.sleep(5)

    if timeout <= 0:
        logger.error("Timeout! The event is %s" % STATE)
        return 1

    return 0


def resume_event(domobj, guestname, timeout, logger):
    """resume the guest, then check the event infomation"""
    global STATE
    STATE = None
    logger.info("resume guest %s" % guestname)
    try:
        domobj.resume()
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        logger.error("Error: fail to resume %s" % guestname)
        return 1

    while timeout:
        if STATE == "Resumed":
            logger.info("The event is Resumed, PASS")
            break
        elif STATE is not None:
            logger.debug("The event is %s", STATE)
        else:
            timeout -= 5
            time.sleep(5)

    if timeout <= 0:
        logger.error("Timeout! The event is %s" % STATE)
        return 1

    return 0


def pure_eventhandler(params):
    """ perform basic operation for a domain, then checking the result
        by using domain event handler.
    """
    logger = params['logger']
    guestname = params['guestname']
    logger.info("the guestname is %s" % guestname)

    if not version_compare("libvirt-python", 3, 8, 0, logger):
        eventLoopPure(logger)

    conn = libvirt.open(None)

    if check_domain_running(conn, guestname, logger):
        return 1

    domobj = conn.lookupByName(guestname)
    conn.domainEventRegisterAny(None, libvirt.VIR_DOMAIN_EVENT_ID_LIFECYCLE,
                                myDomainEventCallback, logger)

    timeout = 600
    if shutdown_event(domobj, guestname, timeout, logger):
        logger.warn("shutdown_event error")

    if bootup_event(domobj, guestname, timeout, logger):
        logger.warn("bootup_event error")

    if suspend_event(domobj, guestname, timeout, logger):
        logger.warn("suspend_event error")

    if resume_event(domobj, guestname, timeout, logger):
        logger.warn("resume_event error")

    conn.domainEventDeregisterAny(0)
    return 0
