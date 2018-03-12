#!/usr/bin/env python
# To test setPerfEvents() API

import libvirt

from xml.dom import minidom
from libvirt import libvirtError
from src import sharedmod
from utils import utils

required_params = ('guestname',)
optional_params = {'flags': 'current',
                   'cmt': '',
                   'mbmt': '',
                   'mbml': '',
                   'cpu_cycles': '',
                   'instructions': '',
                   'cache_references': '',
                   'cache_misses': '',
                   'branch_instructions': '',
                   'branch_misses': '',
                   'bus_cycles': '',
                   'ref_cpu_cycles': '',
                   'stalled_cycles_backend': '',
                   'stalled_cycles_frontend': '',
                   'alignment_faults': '',
                   'context_switches': '',
                   'cpu_clock': '',
                   'cpu_migrations': '',
                   'emulation_faults': '',
                   'page_faults': '',
                   'page_faults_maj': '',
                   'page_faults_min': '',
                   'task_clock': '',
                   }

XML_PATH = "/var/run/libvirt/qemu/"


def check_events(events, event_list, guestname, flags, domstate, dom, logger):
    values = {}
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
        if i in list(values.keys()) and i in list(events.keys()):
            if values[i] != events[i]:
                return 1

    return 0


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


def get_params(name, params):
    value = params.get(name, '')
    if value == 'enabled':
        return True
    elif value == 'disabled':
        return False
    else:
        return None


def set_perf_events(params):
    """ Test setPerfEvents()
    """
    logger = params['logger']
    guestname = params['guestname']

    if not utils.version_compare("libvirt-python", 1, 3, 5, logger):
        logger.info("Current libvirt-python don't support this API.")
        return 0

    events = {}
    if utils.version_compare("libvirt-python", 3, 2, 0, logger):
        params_list = ('cmt', 'mbmt', 'mbml', 'cpu_cycles', 'instructions',
                       'cache_references', 'cache_misses', 'branch_instructions',
                       'branch_misses', 'bus_cycles', 'ref_cpu_cycles',
                       'stalled_cycles_backend', 'stalled_cycles_frontend',
                       'alignment_faults', 'context_switches', 'cpu_clock',
                       'cpu_migrations', 'emulation_faults', 'page_faults',
                       'page_faults_maj', 'page_faults_min', 'task_clock')
    else:
        params_list = ('cmt', 'mbmt', 'mbml')

    for i in params_list:
        if get_params(i, params) is None:
            continue
        else:
            events[i] = get_params(i, params)
    logger.info("events: %s" % events)

    flags = parse_flag(params, logger)
    if flags == -1:
        return 1

    try:
        conn = sharedmod.libvirtobj['conn']
        dom = conn.lookupByName(guestname)
        domstate = dom.state(0)[0]
        dom.setPerfEvents(events, flags)
    except libvirtError as e:
        logger.error("API error message: %s, error code: %s" %
                     (e.message, e.get_error_code()))
        # For REHL 7.4
        err_str = ("argument unsupported: unable to enable host cpu perf event for")
        if (err_str in e.message):
            return 0

        # For RHEL 7.3
        err_str = ("Failed to open file '/sys/devices/intel_cqm/type': No such file or directory")
        if (err_str in e.message):
            return 0

        # For RHEL 7.3, when cmt/mbmt/mbml status are 'disable', they can't be disabled again.
        err_str = ("Unable to disable perf event type=")
        if (err_str in e.message and e.get_error_code() == 38):
            return 0

        return 1

    if check_events(events, params_list, guestname, flags, domstate, dom, logger):
        logger.error("Fail: set perf events failed.")
        return 1
    else:
        logger.info("Pass: set perf events successful.")

    return 0
