#!/usr/bin/env python
"""Sets state of individual vcpus described by @cpumap via guest
   agent.This API requires the VM to run. Various hypervisors or
   guest agent implementation may limit to operate on just 1
   vCPU per call.
"""

import time
from libvirt import libvirtError
from src import sharedmod
from utils import utils

required_params = ('guestname', 'username', 'password')
optional_params = {}


def check_result(domobj, logger, vcpu, username, password, ip, state):
    #check whether or not setGuestVcpus is successful

    cmd = "cat /sys/devices/system/cpu/offline"
    ret, output = utils.remote_exec_pexpect(ip, username, password, cmd)
    cmd1 = "cat /sys/devices/system/cpu/online"
    ret1, output1 = utils.remote_exec_pexpect(ip, username, password, cmd1)
    if not state:
        if output != "2-%s" % str(vcpu - 1) or output1 != "0-1":
            logger.error("set guest vcpus fail!")
            return 1
    else:
        if output != "" or output1 != "0-%s" % str(vcpu - 1):
            logger.error("set guest vcpus fail!")
            return 1
    return 0


def setGuestVcpus_state(domobj, logger, vcpu, username, password, cpumap, ip, state):
    # to simplify the code
    try:
        domobj.setGuestVcpus(cpumap, state, 0)
        logger.info("set guest cpu %s state to %s" % (cpumap, state))
    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    ret = check_result(domobj, logger, vcpu, username, password, ip, state)
    if ret != 0:
        return 1
    return 0


def set_guest_vcpus(params):
    """Sets state of individual vcpus described by @cpumap via guest agen
       t.This API requires the VM to run. Various hypervisors or guest agent
       implementation may limit to operate on just 1 vCPU per call.
    """

    logger = params['logger']
    guestname = params['guestname']
    username = params['username']
    password = params['password']

    conn = sharedmod.libvirtobj['conn']
    domobj = conn.lookupByName(guestname)

    logger.info("the name of virtual machine is %s" % guestname)

    logger.info("get the mac address of vm %s" % guestname)
    mac = utils.get_dom_mac_addr(guestname)
    logger.info("the mac address of vm %s is %s" % (guestname, mac))

    timeout = 300

    while timeout:
        time.sleep(10)
        timeout -= 10

        ip = utils.mac_to_ip(mac, 180)

        if not ip:
            logger.info(str(timeout) + "s left")
        else:
            logger.info("the ip address of vm %s is %s" % (guestname, ip))
            break

    if timeout == 0:
        logger.info("fail to power on vm %s" % guestname)
        return 1

    cmd = "cat /proc/cpuinfo | grep processor | wc -l"
    ret, output = utils.remote_exec_pexpect(ip, username, password, cmd)
    if not ret:
        logger.info("cpu number in domain is %s" % output)
        vcpu = int(output)
    else:
        logger.error("get cpu in domain fail")
        return 1

    #set vcpu except vcpu number 0,1
    cpumap = "1-%d,^1" % (vcpu - 1)

    #set guest state to offline
    ret = setGuestVcpus_state(domobj, logger, vcpu, username, password, cpumap, ip, 0)
    if ret:
        logger.error("set guest vcpus to offline fail!")
        return 1
    #set guest state to online
    ret = setGuestVcpus_state(domobj, logger, vcpu, username, password, cpumap, ip, 1)
    if ret:
        logger.error("set guest vcpus to online fail!")
        return 1
    logger.info("set guest vcpus successful")
    logger.info("PASS")
    return 0
