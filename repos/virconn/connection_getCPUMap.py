#!/usr/bin/env python
# test libvirt getCPUMap API

import commands
import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ()
optional_params = {'conn': ''}


def gen_hostcpu_online_map():
    total = int(commands.getoutput(
        "lscpu | grep '^CPU(s):' | awk '{print $2}'"))
    online = commands.getoutput(
        "cat /proc/cpuinfo | grep '^processor' | awk '{print $3}'").split('\n')
    online_num = len(online)
    online_map = map(lambda cpu_num:
                     True if str(cpu_num) in online else False,
                     range(total))
    return (total, online_map, online_num)


def connection_getCPUMap(params):
    """test libvirt connection getCPUMap
    """
    logger = params['logger']

    try:
        # get connection firstly.
        # If conn is not specified, use conn from sharedmod
        if 'conn' in params:
            conn = libvirt.open(params['conn'])
        else:
            conn = sharedmod.libvirtobj['conn']

        result = conn.getCPUMap()
        expect = gen_hostcpu_online_map()

    except libvirtError, e:
        logger.error("API error message: %s, error code is %s" %
                     e.message)
        logger.error("getCPUMap failed")
        return 1

    logger.info("Expect: " + str(expect))
    logger.info("Get: " + str(result))

    if result != expect:
        logger.error("getCPUMap fail.")
        return 1

    return 0
