#!/usr/bin/env python
# test getCPUModelNames() API for libvirt0

import os

from xml.dom import minidom
from libvirt import libvirtError
from src import sharedmod

required_params = ('arch',)
optional_params = {}

CPU_MAP_FILE = "/usr/share/libvirt/cpu_map.xml"
CPU_MAP_DIR = "/usr/share/libvirt/cpu_map"


def get_cpu_archs_list(filename, logger):
    """
       return supported cpu archs
    """
    cpu_archs_list = []
    xml = minidom.parse(filename)
    for arch in xml.getElementsByTagName('arch'):
        cpu_archs_list.append(str(arch.getAttribute('name')))
    return cpu_archs_list


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


def get_cpu_models_list(arch, logger):
    """
       return supported cpu models
    """
    cpu_models_list = []
    model_file_list = []
    if arch == 'x86_64' or arch == 'i686':
        real_arch = 'x86'
    else:
        real_arch = arch

    xml = minidom.parse(CPU_MAP_DIR + '/index.xml')
    for include in xml.getElementsByTagName('include'):
        model_filename = include.getAttribute('filename')
        if ('vendors' not in model_filename
                and 'features' not in model_filename
                and real_arch in model_filename):
            model_file_list.append(model_filename)
    for model_file in model_file_list:
        model = minidom.parse(CPU_MAP_DIR + '/' + model_file).getElementsByTagName('model')
        cpu_models_list.append(model[0].getAttribute('name'))
    return cpu_models_list


def connection_cpu_models(params):
    """
       test API for getCPUModelNames in class virConnect
    """
    logger = params['logger']
    arch_value = params['arch']

    logger.info("get cpu archs and models list")
    cpu_archs_list = []
    cpu_models_list = []
    if os.path.exists(CPU_MAP_FILE):
        cpu_archs_list = get_cpu_archs_list(CPU_MAP_FILE, logger)
        cpu_models_list = get_cpu_models_from_xml(arch_value, logger)
    elif os.path.exists(CPU_MAP_DIR):
        cpu_archs_list = get_cpu_archs_list(CPU_MAP_DIR + '/index.xml', logger)
        cpu_models_list = get_cpu_models_list(arch_value, logger)
    else:
        logger.error("%s or %s don't exist." % (CPU_MAP_FILE, CPU_MAP_DIR))
        return 1
    logger.info("The supported cpu archs: %s" % cpu_archs_list)
    logger.info("The supported cpu models: %s" % cpu_models_list)

    try:
        conn = sharedmod.libvirtobj['conn']
        cpu_models_from_libvirt = conn.getCPUModelNames(arch_value, 0)
        logger.info("The specified architecture is %s"
                    % arch_value)
        logger.info("The libvirt supported cpu models is %s"
                    % cpu_models_from_libvirt)

        # compare with cpu_map.xml
        for cpu_model in cpu_models_from_libvirt:
            if cpu_model in cpu_models_list:
                logger.debug("'%s' model: PASS" % cpu_model)
            else:
                logger.debug("'%s' model: FAIL, not in libvirt"
                             % cpu_model)
                return 1
        logger.debug("check all cpu models: PASS")
    except libvirtError as e:
        logger.error("API error message: %s" % e.get_error_message())
        return 1

    return 0
