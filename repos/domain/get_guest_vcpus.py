#!/usr/bin/env python
# get guest vcpus

import time
from libvirt import libvirtError

from src import sharedmod
from utils import utils
from repos.installation import install_common

required_params = ('guestname',)
optional_params = {}


def get_guest_ip(guestname, logger, bridge='virbr0'):
    mac = utils.get_dom_mac_addr(guestname)

    logger.info("MAC address: %s" % mac)

    timeout = 300
    while timeout:
        time.sleep(10)
        timeout -= 10
        ip = utils.mac_to_ip(mac, 180, bridge)

        if not ip:
            logger.info(str(timeout) + "s left")
        else:
            logger.info("Guest %s start successfully" % guestname)
            logger.info("IP address: %s" % ip)
            break

    if timeout == 0:
        logger.info("Guest %s start failed." % guestname)
        return None
    return ip


def check_domain_running(conn, guestname, logger):
    """ check if the domain exists, may or may not be active """
    guest_names = []
    ids = conn.listDomainsID()
    for id in ids:
        obj = conn.lookupByID(id)
        guest_names.append(obj.name())

    if guestname not in guest_names:
        logger.error("%s doesn't exist or not running" % guestname)
        return 1
    else:
        return 0


def check_guest_vcpus(ip, info, logger):
    username = install_common.get_value_from_global("variables", "username")
    passwd = install_common.get_value_from_global("variables", "password")
    cmd = "lscpu | grep 'On-line CPU(s) list' | awk '{print $4}'"
    ret, out = utils.remote_exec_pexpect(ip, username, passwd, cmd)
    if ret:
        logger.error("Get guest online cpu list failed.")
        logger.error("ret: %s, out: %s" % (ret, out))
        return 1

    if info['online'] != out:
        return 1

    cmd = "lscpu | grep '^CPU(s)' | awk '{print $2}'"
    ret, out = utils.remote_exec_pexpect(ip, username, passwd, cmd)
    if ret:
        logger.error("Get guest cpu failed.")
        logger.error("ret: %s, out: %s" % (ret, out))
        return 1

    vcpu = "0-" + str(int(out) - 1)
    if info['vcpus'] != vcpu and info['offlinable'] != vcpu:
        return 1

    return 0


def get_guest_vcpus(params):
    logger = params['logger']
    guestname = params['guestname']

    if not utils.version_compare("libvirt-python", 2, 5, 0, logger):
        logger.info("Current libvirt-python don't support this API.")
        return 0

    try:
        conn = sharedmod.libvirtobj['conn']
        ret = check_domain_running(conn, guestname, logger)
        if ret:
            return 1

        domobj = conn.lookupByName(guestname)
        ip = get_guest_ip(guestname, logger)
        info = domobj.guestVcpus()
        logger.info("Guest vcpus: %s" % info)
        if check_guest_vcpus(ip, info, logger):
            logger.error("FAIL: get guest vcpus failed.")
            return 1
        else:
            logger.info("PASS: get guest vcpus successful.")
            return 0

    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    return 0
