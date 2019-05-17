#!/usr/bin/env python
# Test set domain balloon memory with flag VIR_DOMAIN_AFFECT_LIVE.
# Check domain info and inside domain to get current memory value.
# The live flag only work on running domain, so test on shutoff
# domain will fail.

import time
import math
import functools

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('guestname', 'memory', 'username', 'password', )
optional_params = {}


def compare_memory(expect_memory, actual_memory):
    """ comparing expected memory size with actual memory size """

    logger.info("expected memory size is %s" % expect_memory)
    logger.info("actual memory size is %s" % actual_memory)
    diff = int(expect_memory) - int(actual_memory)

    if math.fabs(diff) / expect_memory < 0.05:
        return 0
    else:
        return 1


def get_reserved_memory(guestname, username, password):
    """get domain reserved memory
    """
    logger.debug("get the mac address of vm %s" % guestname)
    mac = utils.get_dom_mac_addr(guestname)
    logger.debug("the mac address of vm %s is %s" % (guestname, mac))
    ip = utils.mac_to_ip(mac, 180)
    current = utils.get_remote_memory(ip, username, password)
    avaliable = utils.get_remote_memory(ip, username, password, "MemTotal")

    return current - avaliable


def get_current_memory(guestname, username, password):
    """get domain current memory inside domain
    """
    logger.debug("get the mac address of vm %s" % guestname)
    mac = utils.get_dom_mac_addr(guestname)
    logger.debug("the mac address of vm %s is %s" % (guestname, mac))
    ip = utils.mac_to_ip(mac, 180)
    current = utils.get_remote_memory(ip, username, password, "MemTotal")

    return current


def check_dom_current_mem(domobj, memory, logger):
    dominfo = domobj.info()
    logger.debug("domain info: %s" % dominfo)
    if dominfo[2] >= memory and dominfo[2] <= 2516582:
        return True
    else:
        return False


def set_memory_live(params):
    """set domain memory with live flag and check
    """
    global logger
    logger = params['logger']
    params.pop('logger')
    guestname = params['guestname']
    memory = int(params['memory'])
    username = params['username']
    password = params['password']

    if utils.isPower():
        # in get_remote_memory(): cat /proc/meminfo | grep DirectMap | awk '{print $2}'
        logger.info("Don't support 'DirectMap' on ppc arch which lead to check memory failed.")
        return 0

    logger.info("the name of virtual machine is %s" % guestname)
    logger.info("the given memory value is %s" % memory)

    conn = sharedmod.libvirtobj['conn']

    try:
        domobj = conn.lookupByName(guestname)
        max_mem = domobj.maxMemory()
        domobj.setMemoryFlags(max_mem, libvirt.VIR_DOMAIN_AFFECT_LIVE)
        logger.info("set domain memory to max mem %s with flag: %s" %
                    (str(max_mem), libvirt.VIR_DOMAIN_AFFECT_LIVE))
        time.sleep(3)
        reserved = get_reserved_memory(guestname, username, password)
        logger.info("set domain memory as %s with flag: %s" %
                    (memory, libvirt.VIR_DOMAIN_AFFECT_LIVE))
        domobj.setMemoryFlags(memory, libvirt.VIR_DOMAIN_AFFECT_LIVE)
        logger.info("get domain current memory")

        ret = utils.wait_for(functools.partial(check_dom_current_mem, domobj, memory, logger), 60, step=5)
        if ret:
            logger.info("set memory match with domain info")
        else:
            logger.error("set memory not match with domain info")
            return 1

        logger.info("check domain memory inside domain")
        ret = get_current_memory(guestname, username, password)
        if not compare_memory(memory, ret + reserved):
            logger.info("set domain memory succeed")
        else:
            logger.error("set domain memory failed")
            return 1

    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    return 0
