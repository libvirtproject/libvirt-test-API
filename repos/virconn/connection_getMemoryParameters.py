#!/usr/bin/env python

import libvirt
from libvirt import libvirtError

required_params = ()
optional_params = {'conn': ''}
node_memory = ['full_scans',
               'merge_across_nodes',
               'pages_shared',
               'pages_sharing',
               'pages_to_scan',
               'pages_unshared',
               'pages_volatile',
               'sleep_millisecs']

SYSFS_MEMORY_SHARED_PATH = '/sys/kernel/mm/ksm/'
flags = 0


def check_memory_parameter(libvirt_dict, parameter_name):
    a = libvirt_dict.get('shm_%s' % parameter_name)
    try:
        b = long(
            open(
                '%s%s' %
                (SYSFS_MEMORY_SHARED_PATH, parameter_name)).read())
    except IOError:
        logger.info("Cannot get file in path %s%s"
                    % (SYSFS_MEMORY_SHARED_PATH, parameter_name))
        return 1
    logger.info("equal %s : libvirt get %u and we get %u"
                % (parameter_name, a, b))
    if a == b:
        return 0
    else:
        return 1


def connection_getMemoryParameters(params):
    """
       test API for getMemoryParameters in class virConnect
    """
    global logger
    logger = params['logger']
    fail = 0

    try:
        conn = libvirt.open(params['conn'])

        logger.info("get connection to libvirtd")

        param_dict = conn.getMemoryParameters()

        for n in node_memory:
            fail = check_memory_parameter(param_dict, n)

    except libvirtError as e:
        logger.error("API error message: %s" % e.message)
        fail = 1
    return fail
