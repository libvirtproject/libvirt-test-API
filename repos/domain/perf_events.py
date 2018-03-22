#!/usr/bin/env python
# To test perfEvents() API

import libvirt

from xml.dom import minidom
from libvirt import libvirtError
from src import sharedmod
from utils import utils

required_params = ('guestname',)
optional_params = {'flags': 'current'}

XML_PATH = "/var/run/libvirt/qemu/"


def parse_flag(params, logger):
    flags = params.get('flags', 'current')
    logger.info("Flag: %s" % flags)
    if flags == "current":
        return libvirt.VIR_DOMAIN_AFFECT_CURRENT
    elif flags == "live":
        return libvirt.VIR_DOMAIN_AFFECT_LIVE
    elif flags == "config":
        return libvirt.VIR_DOMAIN_AFFECT_CONFIG
    else:
        logger.error("Not support flag: %s" % flags)
        return -1


def check_events(events, guestname, flags, domstate, dom, logger):
    if utils.version_compare("libvirt-python", 3, 2, 0, logger):
        values = {'cmt': False, 'mbml': False, 'mbmt': False, 'cpu_cycles': False,
                  'instructions': False, 'cache_references': False,
                  'cache_misses': False, 'branch_instructions': False,
                  'branch_misses': False, 'bus_cycles': False,
                  'ref_cpu_cycles': False, 'stalled_cycles_backend': False,
                  'stalled_cycles_frontend': False, 'alignment_faults': False,
                  'context_switches': False, 'cpu_clock': False,
                  'cpu_migrations': False, 'emulation_faults': False,
                  'page_faults': False, 'page_faults_maj': False,
                  'page_faults_min': False, 'task_clock': False}
        event_list = ('cmt', 'mbmt', 'mbml', 'cpu_cycles', 'instructions',
                      'cache_references', 'cache_misses', 'branch_instructions',
                      'branch_misses', 'bus_cycles', 'ref_cpu_cycles',
                      'stalled_cycles_backend', 'stalled_cycles_frontend',
                      'alignment_faults', 'context_switches', 'cpu_clock',
                      'cpu_migrations', 'emulation_faults', 'page_faults',
                      'page_faults_maj', 'page_faults_min', 'task_clock')
    else:
        values = {'cmt': False, 'mbml': False, 'mbmt': False}
        event_list = ('cmt', 'mbmt', 'mbml')

    if ((domstate == libvirt.VIR_DOMAIN_RUNNING) and
        ((flags == libvirt.VIR_DOMAIN_AFFECT_CURRENT) or
         (flags == libvirt.VIR_DOMAIN_AFFECT_LIVE))):
        xmlstr = minidom.parse("%s%s.xml" % (XML_PATH, guestname))
    else:
        guestxml = dom.XMLDesc(libvirt.VIR_DOMAIN_XML_INACTIVE)
        xmlstr = minidom.parseString(guestxml)

    perf = xmlstr.getElementsByTagName('perf')
    if perf:
        perf = xmlstr.getElementsByTagName('perf')[0]
        for item in perf.getElementsByTagName('event'):
            for i in event_list:
                if item.getAttribute('name') == i:
                    if item.getAttribute('enabled') == "yes":
                        values[i] = True
                    elif item.getAttribute('enabled') == "no":
                        values[i] = False

    logger.info("values: %s" % values)
    for i in event_list:
        if values[i] != events[i]:
            return 1

    return 0


def perf_events(params):
    """ Test perfEvents()
    """
    logger = params['logger']
    guestname = params['guestname']

    if not utils.version_compare("libvirt-python", 1, 3, 5, logger):
        logger.info("Current libvirt-python don't support this API.")
        return 0

    flags = parse_flag(params, logger)
    if flags == -1:
        return 1

    try:
        conn = sharedmod.libvirtobj['conn']
        dom = conn.lookupByName(guestname)
        domstate = dom.state(0)[0]
        events = dom.perfEvents(flags)
        logger.info("perf events: %s" % events)

    except libvirtError as e:
        logger.error("API error message: %s, error code: %s" %
                     (e.get_error_message(), e.get_error_code()))
        return 1

    if check_events(events, guestname, flags, domstate, dom, logger):
        logger.error("Fail: get perf events failed.")
        return 1
    else:
        logger.info("Pass: get perf events successful.")

    return 0
