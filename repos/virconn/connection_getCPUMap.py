#!/usr/bin/env python
# test libvirt getCPUMap API

import libvirt
from libvirt import libvirtError
from utils import process
from src import sharedmod

required_params = ()
optional_params = {'conn': ''}


def gen_hostcpu_online_map():
    cmd = "lscpu | grep '^CPU(s):' | awk '{print $2}'"
    output = process.system_output(cmd, shell=True, ignore_status=True)
    total = int(output)

    cmd = "cat /proc/cpuinfo | grep '^processor' | awk '{print $3}'"
    output = process.system_output(cmd, shell=True, ignore_status=True)
    online = output.split('\n')

    online_num = len(online)
    online_map = list(map(lambda cpu_num: True if str(cpu_num) in online else False, range(total)))
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

    except libvirtError as e:
        logger.error("API error message: %s, error code is %s" %
                     e.get_error_message())
        logger.error("getCPUMap failed")
        return 1

    logger.info("Expect: " + str(expect))
    logger.info("Get: " + str(result))

    if result != expect:
        logger.error("getCPUMap fail.")
        return 1

    return 0
