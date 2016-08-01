#!/usr/bin/env python
# To test setPerfEvents() API

import os
import libvirt

from xml.dom import minidom
from libvirt import libvirtError

required_params = ('guestname', 'flags',)
optional_params = {'cmt': 'True',
                   'mbmt': 'True',
                   'mbml': 'True'}

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

    if 'cmt' in events.keys():
        if compare_value('cmt', cmt, events['cmt']):
            return 1

    if 'mbml' in events.keys():
        if compare_value('mbml', mbml, events['mbml']):
            return 1

    if 'mbmt' in events.keys():
        if compare_value('mbmt', mbmt, events['mbmt']):
            return 1

    return 0


def set_perf_events(params):
    """ Test setPerfEvents()
    """
    logger = params['logger']
    guestname = params['guestname']
    flags = params['flags']

    events = {}
    cmt = params.get('cmt')
    if cmt == 'enable':
        events['cmt'] = True
    elif cmt == 'disable':
        events['cmt'] = False

    mbmt = params.get('mbmt')
    if mbmt == 'enable':
        events['mbmt'] = True
    elif mbmt == 'disable':
        events['mbmt'] = False

    mbml = params.get('mbml')
    if mbml == 'enable':
        events['mbml'] = True
    elif mbml == 'disable':
        events['mbml'] = False

    try:
        conn = libvirt.open('qemu:///system')
        dom = conn.lookupByName(guestname)
        dom.setPerfEvents(events, int(flags))
        logger.info("set perf events: %s" % events)

    except libvirtError, e:
        logger.error("API error message: %s, error code: %s" %
                     (e.message, e.get_error_code()))
        err_str = ("Failed to open file '/sys/devices/intel_cqm/type'"
                   ": No such file or directory")
        if ((not os.path.exists(TYPE_FILE)) and (err_str in e.message)):
            logger.info("When host don't support CMT, the path of"
                        " '/sys/devices/intel_cqm/type' don't exist.")
            return 0

        return 1

    if check_events(events, guestname):
        logger.error("Fail: set perf events failed.")
        return 1
    else:
        logger.info("Pass: set perf events successful.")

    return 0
