#!/usr/bin/env python
# test compareHypervisorCPU()

import libvirt

from libvirt import libvirtError
from xml.dom import minidom

from src import sharedmod
from utils.utils import version_compare

required_params = ('emulator', 'arch', 'machine', 'virttype', 'scenario')
optional_params = {}


def compare_hypervisor_cpu(params):
    logger = params['logger']
    emulator = params['emulator']
    arch = params['arch']
    machine = params['machine']
    virttype = params['virttype']
    scenario = params['scenario']

    if not version_compare("libvirt-python", 4, 4, 0, logger):
        logger.info("Current libvirt-python don't support "
                    "compareHypervisorCPU().")
        return 0

    try:
        if 'conn' in params:
            conn = libvirt.open(params['conn'])
        else:
            conn = sharedmod.libvirtobj['conn']

        if scenario == "capabilities":
            all_caps = conn.getCapabilities()
            xml = minidom.parseString(all_caps)
            host_cpu = xml.getElementsByTagName('cpu')[0].toxml()
        elif scenario == "domcapabilities":
            all_caps = conn.getDomainCapabilities(emulator, arch, machine, virttype, 0)
            xml = minidom.parseString(all_caps)
            host_cpu = xml.getElementsByTagName('cpu')[0].toxml()
        elif scenario == "passthrough":
            host_cpu = "<cpu mode='host-passthrough' check='none'/>"
        else:
            logger.error("Don't support %s scenario.")
            return 1

        logger.debug("Host cpu xml: " + str(host_cpu))
        ret = conn.compareHypervisorCPU(emulator, arch, machine, virttype, host_cpu, 0)
        if scenario == "capabilities" and ret == 0:
            logger.info("compare hypervisor cpu successful.")
        elif (scenario == "domcapabilities" or scenario == "passthrough") and ret == 2:
            logger.info("compare hypervisor cpu successful.")
        else:
            logger.error("compare hypervisor cpu failed.")
            return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s" %
                     (e.get_error_message(), e.get_error_code()))
        return 1

    return 0
