#!/usr/bin/env python

import libvirt
from libvirt import libvirtError

required_params = ()
optional_params = {'uri': None}
node_memory = ['full_scans',
               'merge_across_nodes',
               'pages_shared',
               'pages_sharing',
               'pages_to_scan',
               'pages_unshared',
               'pages_volatile',
               'sleep_millisecs']

MEMORY_SHARED_PATH = '/sys/kernel/mm/ksm/'
flags = 0


def check_memory_parameter(libvirt_dict, parameter_name, logger):
    libvirt_params = libvirt_dict.get('shm_%s' % parameter_name)
    api_params = ""
    try:
        temp_str = open('%s%s' % (MEMORY_SHARED_PATH, parameter_name), 'rb').read()
        api_params = temp_str.decode().rstrip('\n')
    except IOError:
        logger.info("Cannot get file in path %s%s"
                    % (MEMORY_SHARED_PATH, parameter_name))
        return 1
    logger.info("equal %s : libvirt get %s and we get %s"
                % (parameter_name, libvirt_params, api_params))
    if libvirt_params == int(api_params):
        return 0
    else:
        return 1


def connection_getMemoryParameters(params):
    """
       test API for getMemoryParameters in class virConnect
    """
    logger = params['logger']
    uri = params.get("uri", None).decode()
    fail = 0

    try:
        conn = libvirt.open(uri)
        logger.info("get connection to libvirtd")
        param_dict = conn.getMemoryParameters()

        for n in node_memory:
            fail = check_memory_parameter(param_dict, n, logger)

    except libvirtError as e:
        logger.error("API error message: %s" % e.message)
        fail = 1
    return fail
