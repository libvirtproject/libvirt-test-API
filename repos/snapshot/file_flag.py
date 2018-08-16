#!/usr/bin/env python
# Create a flag file in the guest OS

import time

from src import sharedmod
from utils import utils

required_params = ('guestname', 'username', 'password',)
optional_params = {}

FLAG_FILE = "snapshot_flag"
MAKE_FLAG = "rm -f /tmp/%s; touch /tmp/%s " % (FLAG_FILE, FLAG_FILE)


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


def make_flag(ipaddr, username, password, logger):
    """ enter guest OS, create a file in /tmp folder """
    ret, out = utils.remote_exec_pexpect(ipaddr, username, password, MAKE_FLAG)
    if ret:
        logger.error("connecting to guest OS timeout")
        return False
    elif out != '':
        logger.error("failed to make flag in guest OS, %s" % out)
        return False
    else:
        logger.info("flag %s is created in /tmp folder" % FLAG_FILE)
        return True


def file_flag(params):
    """ create a new file in the /tmp folder of the guest
        as a flag
    """
    logger = params['logger']
    guestname = params['guestname']
    username = params['username']
    password = params['password']

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

    if not make_flag(ipaddr, username, password, logger):
        logger.error("making flag in guest %s failed" % guestname)
        return 1
    else:
        logger.info("making flag in guest %s succeeded" % guestname)

    return 0
