#!/usr/bin/env python

import os
import sys
import re
import time

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('guestname', 'username', 'password',)
optional_params = {'expectedret': ''}

FLAG_FILE = "/tmp/snapshot_flag"
FLAG_CHECK = "ls %s" % FLAG_FILE


def check_domain_running(conn, guestname, logger):
    """ check if the domain exists and in running state as well """
    guest_names = []
    ids = conn.listDomainsID()
    for id in ids:
        obj = conn.lookupByID(id)
        guest_names.append(obj.name())

    if guestname not in guest_names:
        logger.error("%s is not running or does not exist" % guestname)
        return False
    else:
        return True


def flag_check(params):
    """ check if the flag file is present or not"""
    logger = params['logger']
    guestname = params['guestname']
    username = params['username']
    password = params['password']

    if 'expectedret' in params:
        expected_result = params['expectedret']
    else:
        expected_result = "exist"

    conn = sharedmod.libvirtobj['conn']

    if not check_domain_running(conn, guestname, logger):
        logger.error("need a running guest")
        return 1

    logger.info("get the mac address of vm %s" % guestname)
    mac = utils.get_dom_mac_addr(guestname)
    logger.info("the mac address of vm %s is %s" % (guestname, mac))

    timeout = 300
    while timeout:
        ipaddr = utils.mac_to_ip(mac, 180)
        if not ipaddr:
            logger.info(str(timeout) + "s left")
            time.sleep(10)
            timeout -= 10
        else:
            logger.info("the ip address of vm %s is %s" % (guestname, ipaddr))
            break

    if timeout == 0:
        logger.info("vm %s failed to get ip address" % guestname)
        return 1

    ret, out = utils.remote_exec_pexpect(
        ipaddr, username, password, FLAG_CHECK)
    if ret:
        logger.error("connecting to guest OS timeout")
        return 1
    elif out == FLAG_FILE and expected_result == "exist":
        logger.info("checking flag %s in guest OS succeeded" % FLAG_FILE)
        return 0
    elif out == FLAG_FILE and expected_result == 'noexist':
        logger.error("flag %s still exist, FAILED." % FLAG_FILE)
        return 1
    elif out is not None and expected_result == "exist":
        logger.error("no flag %s exists in the guest %s " % (FLAG_FILE, guestname))
        return 1
    elif out is not None and expected_result == 'noexist':
        logger.info("flag %s is not present, checking succeeded" % FLAG_FILE)
        return 0

    return 0
