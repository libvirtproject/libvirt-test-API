#!/usr/bin/env python
# Test set domain numa parameters with flag
# VIR_DOMAIN_AFFECT_CONFIG and check

from xml.dom import minidom

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('guestname', 'nodeset', 'mode')
optional_params = {}


def check_numa_params(domobj, mode, node_tuple):
    """dump domain config xml description to check numa params
    """
    guestxml = domobj.XMLDesc(2)
    logger.debug("domain %s xml is :\n%s" % (domobj.name(), guestxml))
    xml = minidom.parseString(guestxml)
    numatune = xml.getElementsByTagName('numatune')[0]
    mem_element = numatune.getElementsByTagName('memory')[0]

    if mem_element.hasAttribute('mode') and \
       mem_element.hasAttribute('nodeset'):
        attr = mem_element.getAttributeNode('mode')
        mode_val = attr.nodeValue
        logger.info("memory mode in config xml is: %s" % mode_val)
        if mode_val == 'strict':
            mode_num = 0
        elif mode_val == 'preferred':
            mode_num = 1
        elif mode_val == 'interleave':
            mode_num = 2
        else:
            logger.error("mode value is invalid")
            return 1

        attr = mem_element.getAttributeNode('nodeset')
        nodeset_val = attr.nodeValue
        logger.info("nodeset in config xml is: %s" % nodeset_val)
    else:
        logger.error("no 'mode' and 'nodeset' atrribute for element memory")
        return 1

    ret = utils.param_to_tuple(nodeset_val, node_num)
    logger.debug("nudeset in config xml to tuple is:")
    logger.debug(ret)
    if not ret:
        logger.error("fail to parse nodeset to tuple")
        return 1

    if mode_num == mode and ret == node_tuple:
        return 0
    else:
        return 1


def numa_param_config(params):
    """set domain numa parameters with config flag and check
    """
    global logger
    logger = params['logger']
    params.pop('logger')
    guestname = params['guestname']
    nodeset = params['nodeset']
    mode = int(params['mode'])

    logger.info("the name of virtual machine is %s" % guestname)
    logger.info("the given node number is: %s" % nodeset)
    logger.info("the given mode is: %s" % mode)

    global node_num
    cmd = "lscpu|grep 'NUMA node(s)'"
    ret, output = utils.exec_cmd(cmd, shell=True)
    node_num = int(output[0].split(' ')[-1])
    node_tuple = utils.param_to_tuple(nodeset, node_num)
    logger.debug("nodeset to tuple is:")
    logger.debug(node_tuple)

    param = {'numa_nodeset': nodeset, 'numa_mode': mode}
    logger.info("numa param dict for set is: %s" % param)

    conn = sharedmod.libvirtobj['conn']

    try:
        domobj = conn.lookupByName(guestname)
        logger.info("set domain numa parameters with flag: %s" %
                    libvirt.VIR_DOMAIN_AFFECT_CONFIG)
        domobj.setNumaParameters(param, libvirt.VIR_DOMAIN_AFFECT_CONFIG)
        logger.info("set domain numa parameters succeed")

        logger.info("check numa parameters")
        ret = domobj.numaParameters(libvirt.VIR_DOMAIN_AFFECT_CONFIG)
        logger.info("numa parameters after set is: %s" % ret)

        new_tuple = utils.param_to_tuple(ret['numa_nodeset'], node_num)
        if not new_tuple:
            logger.error("fail to parse nodeset to tuple")
            return 1

        if new_tuple == node_tuple and ret['numa_mode'] == mode:
            logger.info("numa parameters is as expected")
        else:
            logger.error("numa parameters is not as expected")
            return 1

    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    logger.info("check domain config xml of numa params")
    ret = check_numa_params(domobj, mode, node_tuple)
    if ret:
        logger.error("numa params in domain config xml are not expected")
        return 1
    else:
        logger.info("numa params in domain config xml are expected")
        return 0
