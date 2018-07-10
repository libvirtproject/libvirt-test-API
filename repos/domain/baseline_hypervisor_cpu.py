#!/usr/bin/env python
# test baselineHypervisorCPU()

import libvirt
import re
from libvirt import libvirtError
from xml.dom import minidom

from src import sharedmod
from utils.utils import version_compare

required_params = ('emulator', 'arch', 'machine', 'virttype')
optional_params = {}


def get_host_cpu(conn):
    all_caps = conn.getCapabilities()
    xml = minidom.parseString(all_caps)
    return xml.getElementsByTagName('cpu')[0].toxml()


def get_cpu_feature_set(cpu_xml):
    curret_set = re.findall('\s*<feature.*? name=["\'](\S+?)["\']', cpu_xml)
    return set(curret_set)


def baseline_hypervisor_cpu(params):
    logger = params['logger']
    emulator = params['emulator']
    arch = params['arch']
    machine = params['machine']
    virttype = params['virttype']

    if not version_compare("libvirt-python", 4, 4, 0, logger):
        logger.info("Current libvirt-python don't support "
                    "baselineHypervisorCPU().")
        return 0

    try:
        if 'conn' in params:
            conn = libvirt.open(params['conn'])
        else:
            conn = sharedmod.libvirtobj['conn']

        host_cpu = get_host_cpu(conn)
        logger.debug("Host cpu xml: " + str(host_cpu))
        baseline = conn.baselineHypervisorCPU(emulator, arch, machine, virttype, [host_cpu], 0)

        sub_features = get_cpu_feature_set(host_cpu)
        baseline_features = get_cpu_feature_set(baseline)
        logger.info("Expect: %s" % str(sub_features))
        logger.info("Got: %s" % str(baseline_features))
        if sub_features != baseline_features:
            logger.error("baseline hypervisor cpu failed.")
            return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s" %
                     (e.get_error_message(), e.get_error_code()))
        return 1

    logger.info("baseline hypervisor cpu success.")
    return 0
