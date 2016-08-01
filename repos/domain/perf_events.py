#!/usr/bin/env python
# To test perfEvents() API

import os
import libvirt

from xml.dom import minidom
from libvirt import libvirtError

required_params = ('guestname', 'flags',)
optional_params = {}

TYPE_FILE = "/sys/devices/intel_cqm/type"
XML_PATH = "/var/run/libvirt/qemu/"


def compare_value(name, value, event):
    if value == "no" and not event:
        return 0
    elif value == "yes" and not event:
        return 0
    else:
        return 1


def check_events(events, guestname):
    if not os.path.exists(TYPE_FILE):
        if (not events['cmt'] and
                not events['mbmt'] and
                not events['mbml']):
            return 0
        else:
            return 1

    cmt = "no"
    mbml = "no"
    mbmt = "no"
    xmlstr = minidom.parse("%s%s.xml" % (XML_PATH, guestname))
    perf = xmlstr.getElementsByTagName('perf')[0]
    for item in perf.getElementsByTagName('event'):
        if item.getAttribute('name') == "cmt":
            cmt = item.getAttribute('enabled')
        if item.getAttribute('name') == "mbmt":
            mbmt = item.getAttribute('enabled')
        if item.getAttribute('name') == "mbml":
            mbml = item.getAttribute('enabled')

    if compare_value('cmt', cmt, events['cmt']):
        return 1

    if compare_value('mbml', mbml, events['mbml']):
        return 1

    if compare_value('mbmt', mbmt, events['mbmt']):
        return 1

    return 0


def perf_events(params):
    """ Test perfEvents()
    """
    logger = params['logger']
    guestname = params['guestname']
    flags = params['flags']

    try:
        conn = libvirt.open('qemu:///system')
        dom = conn.lookupByName(guestname)
        ret = dom.perfEvents(int(flags))
        logger.info("perf events: %s" % ret)

    except libvirtError, e:
        logger.error("API error message: %s, error code: %s" %
                     (e.message, e.get_error_code()))
        return 1

    if check_events(ret, guestname):
        logger.error("Fail: get perf events failed.")
        return 1
    else:
        logger.info("Pass: get perf events successful.")

    return 0
