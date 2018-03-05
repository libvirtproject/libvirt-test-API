#!/usr/bin/env python
# test getCPUModelNames() API for libvirt0

import os

from xml.dom import minidom
from libvirt import libvirtError
from src import sharedmod

required_params = ('arch',)
optional_params = {}

CPU_MAP_FILE = "/usr/share/libvirt/cpu_map.xml"


def get_cpu_archs_from_xml(logger):
    """
       return supported cpu archs from cpu_map.xml
    """
    cpu_archs_from_xml = []
    xml = minidom.parse(CPU_MAP_FILE)
    for arch in xml.getElementsByTagName('arch'):
        cpu_archs_from_xml.append(str(arch.getAttribute('name')))
    return cpu_archs_from_xml


def get_cpu_models_from_xml(arch, logger):
    """
       return supported cpu models from cpu_map.xml
    """
    cpu_models_from_xml = []
    if arch == 'x86_64' or arch == 'i686':
        real_arch = 'x86'
    else:
        real_arch = arch

    xml = minidom.parse(CPU_MAP_FILE)
    for model in xml.getElementsByTagName('model'):
        if model.parentNode.getAttribute('name') == real_arch:
            cpu_models_from_xml.append(str(model.getAttribute('name')))
    return cpu_models_from_xml


def connection_cpu_models(params):
    """
       test API for getCPUModelNames in class virConnect
    """
    logger = params['logger']
    arch_value = params['arch'].decode()
    try:
        logger.info("get cpu archs from cpu_map.xml")
        if not os.path.exists(CPU_MAP_FILE):
            logger.error("%s is not exist" % CPU_MAP_FILE)
            return 1
        cpu_archs_from_xml = get_cpu_archs_from_xml(logger)
        logger.info("The supported cpu archs in xml are %s"
                    % cpu_archs_from_xml)
        cpu_models_from_xml = get_cpu_models_from_xml(arch_value, logger)
        logger.info("The supported cpu models in xml are %s"
                    % cpu_models_from_xml)

        conn = sharedmod.libvirtobj['conn']

        cpu_models_from_libvirt = conn.getCPUModelNames(arch_value, 0)
        logger.info("The specified architecture is %s"
                    % arch_value)
        logger.info("The supported cpu models is %s"
                    % cpu_models_from_libvirt)

        # compare with cpu_map.xml
        for cpu_model in cpu_models_from_libvirt:
            if cpu_model in cpu_models_from_xml:
                logger.debug("'%s' model: PASS" % cpu_model)
            else:
                logger.debug("'%s' model: FAIL, not in libvirt"
                             % cpu_model)
                return 1
        logger.debug("check all cpu models: PASS")
    except libvirtError as e:
        logger.error("API error message: %s" % e.message)
        return 1

    return 0
