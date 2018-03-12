#!/usr/bin/env python
# Test get domain memory stats

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('guestname', )
optional_params = {}

VIRSH = "virsh qemu-monitor-command"


def get_memory_actual(guestname):
    """get memory stats with virsh commands
    """
    qmp_actual = -1
    cmd = "%s %s '{ \"execute\": \"query-balloon\" }'" % (VIRSH, guestname)
    logger.info("check memory stats with virsh command: %s" % cmd)
    ret, out = utils.exec_cmd(cmd, shell=True)
    out_dict = eval(out[0])
    if "return" in out_dict:
        if "actual" in out_dict['return']:
            qmp_actual = out_dict['return']['actual']
    else:
        return False

    if qmp_actual == -1:
        return False

    logger.info("the memory actual is: %s" % qmp_actual)
    return qmp_actual


def memory_stats(params):
    """get domain memory stats
    """
    global logger
    logger = params['logger']
    guestname = params['guestname']

    logger.info("the name of virtual machine is %s" % guestname)

    conn = sharedmod.libvirtobj['conn']

    try:
        domobj = conn.lookupByName(guestname)
        mem = domobj.memoryStats()
        logger.info("%s memory stats is: %s" % (guestname, mem))
        ret = get_memory_actual(guestname)
        if not ret:
            logger.error("get memory actual with qmp command failed")
            return 1

        if ret == mem['actual'] * 1024:
            logger.info("actual memory is equal to output of qmp command")
        else:
            logger.error("actual memory is not equal to output of qmp command")
            return 1

    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    return 0
