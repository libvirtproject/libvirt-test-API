#!/usr/bin/env python
# test libvirt connection node infomation

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ()
optional_params = {'uri': None}


def get_model(logger):
    """get nodeinfo model
    """
    output = utils.get_host_arch()
    logger.info("model is %s" % output)
    return output


def get_memory(logger):
    """get nodeinfo memory
    """
    output = utils.get_host_memory()
    # the memory value python API returned is devided by 1024
    mem_cap = int(int(output) / 1024)
    logger.info("memory is %s MiB" % mem_cap)
    return mem_cap


def get_cpus(logger):
    """get nodeinfo cpus
    """
    output = utils.get_host_cpus()
    logger.info("cpus is %s" % output)
    return output


def get_cpu_mhz(logger):
    """get nodeinfo cpu_mhz
    """
    output = utils.get_host_frequency()
    cpu_mhz = int(output.split('.')[0])
    logger.info("cpu MHz is %d" % cpu_mhz)
    return cpu_mhz


def get_nodes(logger):
    """get nodeinfo nodes
    """
    cmds = "lscpu | grep 'node(s)' | awk {'print $3'}"
    (status, output) = utils.exec_cmd(cmds, shell=True)
    if status != 0:
        logger.error("Exec_cmd failed: %s" % cmds)
        return ""
    logger.info("nodes is %s" % output[0])
    return int(output[0])


def get_sockets(logger):
    """get nodeinfo sockets
    """
    cmds = "lscpu | grep 'Socket(s)' | awk {'print $2'}"
    (status, output) = utils.exec_cmd(cmds, shell=True)
    if status != 0:
        logger.error("Exec_cmd failed: %s" % cmds)
        return ""
    logger.info("cpu sockets is %s" % output[0])
    return int(output[0])


def get_cores(logger):
    """get nodeinfo cores
    """
    cmds = "lscpu | grep 'Core(s)' | awk {'print $4'}"
    (status, output) = utils.exec_cmd(cmds, shell=True)
    if status != 0:
        logger.error("Exec_cmd failed: %s" % cmds)
        return ""
    logger.info("cpu cores is %s" % output[0])
    return int(output[0])


def get_threads(logger):
    """get nodeinfo threads
    """
    cmds = "lscpu | grep 'Thread(s)' | awk {'print $4'}"
    (status, output) = utils.exec_cmd(cmds, shell=True)
    if status != 0:
        logger.error("Exec_cmd failed: %s" % cmds)
        return ""
    logger.info("cpu threads is %s" % output[0])
    return int(output[0])


def check_conn_nodeinfo(conn_nodeinfo, logger):
    """check each nodeinfo value
    """
    ret = True
    # python2.6 does not have ordered dict, so that enumerate
    # could not get the defined sequence which API getInfo() returned.
    res_types = ['model', 'memory', 'cpus', 'cpu_mhz', 'nodes',
                 'sockets', 'cores', 'threads']
    get_res_func = [get_model, get_memory, get_cpus, get_cpu_mhz,
                    get_nodes, get_sockets, get_cores, get_threads]

    for idx, res in enumerate(zip(res_types, get_res_func)):
        logger.debug("Checking %s" % res[0])
        logger.debug("Executing %s" % res[1])
        get_res = res[1](logger)
        if get_res != conn_nodeinfo[idx]:
            logger.error("Failed to check nodeinfo's %s" % res[0])
            logger.error("%s %s is wrong, should be %s" %
                         (res, conn_nodeinfo[idx], get_res))
            ret = False

    return ret


def connection_nodeinfo(params):
    """test libvirt connection node infomation
    """
    logger = params["logger"]
    uri = params.get("uri", None)

    try:
        # get connection firstly.
        # If uri is not specified, use conn from sharedmod
        if 'uri' in params:
            conn = libvirt.open(uri)
        else:
            conn = sharedmod.libvirtobj['conn']

        logger.info("get connection node infomation")
        conn_nodeinfo = conn.getInfo()
        logger.info("connection node infomation is %s" % conn_nodeinfo)

        check_conn_nodeinfo(conn_nodeinfo, logger)

    except libvirtError as e:
        logger.error("API error message: %s, error code is %s" %
                     (e.get_error_message(), e.get_error_code()))
        return 1

    return 0
