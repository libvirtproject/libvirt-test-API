#!/usr/bin/env python
# Test set domain numa parameters with flag VIR_DOMAIN_AFFECT_LIVE
# and check

from xml.dom import minidom

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('guestname', 'nodeset', 'mode')
optional_params = {}


def check_numa_params(guestname, mode, node_tuple):
    """dump domain live xml description to check numa params and
       check memory allowed list of domain pid
    """
    cmd = "cat /var/run/libvirt/qemu/%s.pid" % guestname
    status, pid = utils.exec_cmd(cmd, shell=True)
    if status:
        logger.error("failed to get the pid of domain %s" % guestname)
        return 1

    cmd = "grep Mems_allowed_list /proc/%s/status" % pid[0]
    status, output = utils.exec_cmd(cmd, shell=True)
    nodeval = output[0].split('\t')[1]
    ret = utils.param_to_tuple(nodeval, node_num)
    logger.info("Mems_allowed_list in domain pid status is: %s" % nodeval)
    logger.debug("parse nodeset to tuple is:")
    logger.debug(ret)
    if not ret:
        logger.error("fail to parse nodeset to tuple")
        return 1

    # TODO: add check for mode

    if ret == node_tuple:
        return 0
    else:
        return 1


def numa_param_live(params):
    """set domain numa parameters with live flag and check
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
                    libvirt.VIR_DOMAIN_AFFECT_LIVE)
        domobj.setNumaParameters(param, libvirt.VIR_DOMAIN_AFFECT_LIVE)
        logger.info("set domain numa parameters succeed")

        logger.info("check numa parameters")
        ret = domobj.numaParameters(libvirt.VIR_DOMAIN_AFFECT_LIVE)
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

    logger.info("check whether numa params is working")
    ret = check_numa_params(guestname, mode, node_tuple)
    if ret:
        logger.error("numa params working as expected")
        return 1
    else:
        logger.info("numa params working as expected")
        return 0
