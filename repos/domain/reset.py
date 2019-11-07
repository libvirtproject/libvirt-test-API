#!/usr/bin/env python

import functools
import time
import libvirt
import tempfile

from libvirt import libvirtError
from utils import utils

required_params = ('guestname', 'username', 'password')
optional_params = {}


def check_file(tmp_file, logger, username, password, ip):
    # Check file in guest
    cmd = "ls %s" % tmp_file
    ret, output = utils.remote_exec_pexpect(ip, username, password, cmd)
    if not ret:
        logger.error("Fail to check %s in guest. File still exist." % tmp_file)
        return False
    return True


def reset(params):
    """
    Reset a domain immediately without any guest OS shutdown
    Return 0 on SUCCESS or 1 on FAILURE
    Note: reset function just a reset of hardware,it don't shutdown guest.
          Resetting a virtual machine does not apply any pending domain
          configuration changes. Changes to the domain's configuration only
          take effect after acomplete shutdown and restart of the domain.
    """
    logger = params['logger']
    guestname = params['guestname']
    username = params['username']
    password = params['password']

    logger.info("Get the MAC address of %s." % guestname)
    mac = utils.get_dom_mac_addr(guestname)
    logger.info("MAC address: %s" % mac)
    logger.info("Get IP by MAC address.")
    ip = utils.mac_to_ip(mac, 180)
    logger.info("IP: %s" % ip)

    try:
        conn = libvirt.open()
        domobj = conn.lookupByName(guestname)
        tmp_file = tempfile.mkdtemp()
        cmd = "rm -rf %s; sync; touch %s; ls %s" % (tmp_file, tmp_file, tmp_file)
        ret, output = utils.remote_exec_pexpect(ip, username, password, cmd)
        if ret:
            logger.error("Fail to create a tmp file in guest.")
            logger.error("ret: %s, out: %s" % (ret, output))
            return 1
        logger.info("Create file in guest: %s" % tmp_file)
        logger.info("Reset now.")
        domobj.reset(0)
        time.sleep(10)
    except libvirtError as err:
        logger.error("API error message: %s, error code is %s"
                     % (err.get_error_message(), err.get_error_code()))
        logger.error("Fail to reset domain.")
        return 1

    logger.info("Check file in guest.")
    ret = utils.wait_for(functools.partial(check_file, tmp_file, logger, username, password, ip), 600)
    if not ret:
        logger.error("FAIL: reset guest failed.")
        return 1

    logger.info("PASS: reset successfully.")
    return 0
