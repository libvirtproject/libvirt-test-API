#!/usr/bin/env python
# Test set domain memory parameters with flag
# VIR_DOMAIN_AFFECT_CONFIG

from xml.dom import minidom

import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ('guestname', 'hard_limit', 'soft_limit', 'swap_hard_limit', )
optional_params = {}

UNLIMITED = 9007199254740991


def get_memory_config(domobj, param_dict):
    """get domain config memory parameters
    """
    new_dict = {}
    try:
        guestxml = domobj.XMLDesc(2)
        logger.debug("domain %s xml is :\n%s" % (domobj.name(), guestxml))
        xml = minidom.parseString(guestxml)
        logger.info("get domain memory parameters in config xml")
        for i in list(param_dict.keys()):
            if xml.getElementsByTagName(i):
                limit_element = xml.getElementsByTagName(i)[0]
                limit = int(limit_element.childNodes[0].data)
                logger.info("%s in config xml is: %s" % (i, limit))
                new_dict[i] = limit
            else:
                logger.info("%s is not in config xml" % i)
                new_dict[i] = 0

    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return False

    return new_dict


def memory_params_config(params):
    """set domain memory parameters with config flag and check
    """
    global logger
    logger = params['logger']
    guestname = params['guestname']
    hard_limit = int(params['hard_limit'])
    soft_limit = int(params['soft_limit'])
    swap_hard_limit = int(params['swap_hard_limit'])

    logger.info("the name of virtual machine is %s" % guestname)
    param_dict = {'hard_limit': hard_limit,
                  'soft_limit': soft_limit,
                  'swap_hard_limit': swap_hard_limit
                  }

    for i in list(param_dict.keys()):
        if param_dict[i] == -1:
            param_dict[i] = UNLIMITED

    logger.info("the param dict for setting is %s" % param_dict)

    conn = sharedmod.libvirtobj['conn']

    try:
        domobj = conn.lookupByName(guestname)
        flags = libvirt.VIR_DOMAIN_AFFECT_CONFIG
        logger.info("set %s memory parameters with flag: %s" %
                    (guestname, flags))
        domobj.setMemoryParameters(param_dict, flags)
        logger.info("set memory parameters done")

        logger.info("get %s memory parameters with flag: %s" %
                    (guestname, flags))
        ret = domobj.memoryParameters(flags)
        logger.info("%s memory parameters is %s" % (guestname, ret))

        if ret == param_dict:
            logger.info("memory parameters is as expected")
        else:
            logger.error("memory parameters is not as expected")
            return 1

        ret = get_memory_config(domobj, param_dict)
        if ret == param_dict:
            logger.info("memory parameters is as expected in config xml")
        else:
            logger.error("memory parameters is not as expected in config xml")
            return 1

    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    return 0
