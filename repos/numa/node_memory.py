#!/usr/bin/env python
# Test get host node memory info, including host free
# memory, node free memory and node memory stats.

import math

from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ()
optional_params = {}

NODE_MEMINFO_PATH = "/sys/devices/system/node/node*/meminfo"


def node_memory(params):
    """test get host node memory info
    """
    logger = params['logger']

    cmd = "lscpu|grep 'NUMA node(s)'"
    ret, output = utils.exec_cmd(cmd, shell=True)
    node_num = int(output[0].split(' ')[-1])
    logger.info("host total nodes number is: %s" % node_num)

    conn = sharedmod.libvirtobj['conn']

    cmd = "grep 'MemFree' %s" % NODE_MEMINFO_PATH
    node_mem = []
    free_total = 0
    ret, out = utils.exec_cmd(cmd, shell=True)
    for i in range(node_num):
        mem_free = int(out[i].split()[-2])
        node_mem.append(mem_free)
        free_total += mem_free

    try:
        logger.info("get host total free memory")
        mem = conn.getFreeMemory() / 1024
        logger.info("host free memory total is: %s KiB" % mem)
        logger.info("free memory collected in %s is: %s KiB" %
                    (NODE_MEMINFO_PATH, free_total))

        if math.fabs(mem - free_total) > 2048:
            logger.error("free memory mismatch with info collected in %s" %
                         NODE_MEMINFO_PATH)
            return 1
        else:
            logger.info("get host free memory succeed")

        logger.info("get free memory of nodes")
        mem_list = []
        node_list = []
        if utils.isPower():
            cmd = "lscpu | grep 'NUMA node.* CPU(s)'"
            ret, output = utils.exec_cmd(cmd, shell=True)
            for i in range(node_num):
                node_list.append(output[i].split()[1].strip('node'))
            ret =conn.getCellsFreeMemory(0, (int(node_list[-1]) + 1))
            for i in range(node_num):
                mem_list.append(int(ret[int(node_list[i])] / 1024))
        else:
            ret = conn.getCellsFreeMemory(0, node_num)
            mem_list = [i / 1024 for i in ret]

        logger.info("node free memory list is: %s" % mem_list)
        logger.info("node free memory list collected in %s is: %s" %
                    (NODE_MEMINFO_PATH, node_mem))

        for i in range(node_num):
            if math.fabs(mem_list[i] - node_mem[i]) > 524288:
                path = NODE_MEMINFO_PATH.replace('*', '%s') % i
                logger.error("node %s free memory mismatch with collected in %s"
                             % (i, path))
                return 1

        logger.info("get node free memory succeed")

        logger.info("get node memory stats")
        node_dict = {}
        for i in range(node_num):
            if utils.isPower():
                ret = conn.getMemoryStats(int(node_list[i]), 0)
            else:
                ret = conn.getMemoryStats(i, 0)
            node_dict[i] = ret
            logger.info("node %s memory stats is: %s" % (i, node_dict[i]))

        node_tmp = {}
        cmd = "grep 'MemFree' %s" % NODE_MEMINFO_PATH
        cmd_new = "grep 'MemTotal' %s" % NODE_MEMINFO_PATH
        ret, out_free = utils.exec_cmd(cmd, shell=True)
        ret, out_total = utils.exec_cmd(cmd_new, shell=True)
        for i in range(node_num):
            dict_tmp = {}
            if utils.isPower():
                path = NODE_MEMINFO_PATH.replace('*', '%s') % int(node_list[i])
            else:
                path = NODE_MEMINFO_PATH.replace('*', '%s') % i
            dict_tmp['free'] = int(out_free[i].split()[-2])
            dict_tmp['total'] = int(out_total[i].split()[-2])
            node_tmp[i] = dict_tmp
            logger.info("node %s memory stats collected in %s is: %s" %
                        (i, path, node_tmp[i]))

        for i in range(node_num):
            if utils.isPower():
                path = NODE_MEMINFO_PATH.replace('*', '%s') % int(node_list[i])
            else:
                path = NODE_MEMINFO_PATH.replace('*', '%s') % i
            if math.fabs(node_tmp[i]['total'] - node_dict[i]['total']) > 524288:
                logger.error("node %s total memory is mismatch with %s" %
                             (i, path))
                return 1

            if math.fabs(node_tmp[i]['free'] - node_dict[i]['free']) > 524288:
                logger.error("node %s free memory is mismatch with %s" %
                             (i, path))
                return 1

        logger.info("get node memory stats succeed")

    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    return 0
