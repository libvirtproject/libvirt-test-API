#!/usr/bin/env python
# Test sendKey()

import time
import libvirt

from libvirt import libvirtError
from src import sharedmod
from utils import utils

TEST_FILE = "/root/testapi"
# for codeset: linux xt atset1 rfb qnum xt_kbd
KEYCODE_1 = [20, 24, 22, 46, 35, 57, 20, 18, 31, 20, 30, 25, 23, 28]
# for codeset: atset2 atset3
KEYCODE_2 = [44, 68, 60, 33, 51, 41, 44, 36, 27, 44, 28, 77, 67, 90]
# for codeset: osx
KEYCODE_3 = [17, 31, 32, 8, 4, 49, 17, 14, 1, 17, 0, 35, 34, 76]
# for codeset: win32
KEYCODE_4 = [84, 79, 85, 67, 72, 32, 84, 69, 83, 84, 65, 80, 73, 13]
# for codeset: usb
KEYCODE_5 = [57, 23, 18, 24, 6, 11, 44, 23, 8, 22, 23, 4, 19, 12, 40]

required_params = ('guestname', 'username', 'password')
optional_params = {'codeset': 'linux'}


def clean_guest(domobj, logger, username, password, ip):
    cmd = "rm -rf %s" % TEST_FILE
    ret, output = utils.remote_exec_pexpect(ip, username, password, cmd)
    if ret:
        logger.error("fail to remote exec cmd: ret: %s, output: %s"
                     % (ret, output))
        return 1
    return 0


def check_file(domobj, logger, username, password, ip):
    cmd = "ls %s" % TEST_FILE
    ret, output = utils.remote_exec_pexpect(ip, username, password, cmd)
    if ret:
        logger.error("fail to remote exec cmd: ret: %s, output: %s"
                     % (ret, output))
        return 1
    return 0


# For test
import aexpect


def login_guest(guestname, username, password, logger):
    cmd = "virsh console %s --force" % guestname
    session = aexpect.ShellSession(cmd)
    try:
        while True:
            match, text = session.read_until_last_line_matches(
                [r"[E|e]scape character is", r"login:",
                 r"[P|p]assword:", session.prompt],
                10, internal_timeout=1)
            if match == 0:
                logger.debug("Got '^]', sending '\\n'")
                session.sendline()
            elif match == 1:
                logger.debug("Got 'login:', sending '%s'", username)
                session.sendline(username)
            elif match == 2:
                logger.debug("Got 'Password:', sending '%s'", password)
                session.sendline(password)
            elif match == 3:
                logger.debug("Got Shell prompt -- logged in")
                break
        session.close()
    except (aexpect.ShellError,
            aexpect.ExpectError) as detail:
        if 'Shell process terminated' not in str(detail):
            logger.error('Expect shell terminated, but found %s'
                         % detail)
        log = session.get_output()
        logger.error("failed login guest: %s" % log)
        session.close()
# end test


def send_key(params):
    """
    Send "touch testapi" to guest. Check the file is exist or not in guest.
    """
    guestname = params['guestname']
    logger = params['logger']
    username = params['username']
    password = params['password']

    codeset = params.get("codeset", "linux")
    logger.info("codeset: %s" % codeset)

    if codeset == "qnum" and not utils.version_compare("libvirt-python", 4, 4, 0, logger):
        logger.info("Current libvirt-python don't support VIR_KEYCODE_SET_QNUM.")
        return 0

    if codeset == "rfb" and utils.version_compare("libvirt-python", 4, 4, 0, logger):
        logger.info("Current libvirt-python don't support VIR_KEYCODE_SET_RFB.")
        return 0

    if codeset == "linux":
        codeset_value = libvirt.VIR_KEYCODE_SET_LINUX
    elif codeset == "xt":
        codeset_value = libvirt.VIR_KEYCODE_SET_XT
    elif codeset == "atset1":
        codeset_value = libvirt.VIR_KEYCODE_SET_ATSET1
    elif codeset == "atset2":
        codeset_value = libvirt.VIR_KEYCODE_SET_ATSET2
    elif codeset == "atset3":
        codeset_value = libvirt.VIR_KEYCODE_SET_ATSET3
    elif codeset == "osx":
        codeset_value = libvirt.VIR_KEYCODE_SET_OSX
    elif codeset == "xt_kbd":
        codeset_value = libvirt.VIR_KEYCODE_SET_XT_KBD
    elif codeset == "usb":
        codeset_value = libvirt.VIR_KEYCODE_SET_USB
    elif codeset == "win32":
        codeset_value = libvirt.VIR_KEYCODE_SET_WIN32
    elif codeset == "rfb":
        codeset_value = libvirt.VIR_KEYCODE_SET_RFB
    elif codeset == "qnum":
        codeset_value = libvirt.VIR_KEYCODE_SET_QNUM
    else:
        logger.error("Don't support %s codeset." % codeset)
        return 1

    logger.info("get the mac address of vm %s" % guestname)
    mac = utils.get_dom_mac_addr(guestname)
    logger.info("the mac address of vm %s is %s" % (guestname, mac))
    logger.info("get ip by mac address")
    ip = utils.mac_to_ip(mac, 180)
    logger.info("the ip address of vm %s is %s" % (guestname, ip))

    try:
        conn = sharedmod.libvirtobj['conn']
        domobj = conn.lookupByName(guestname)
        #login_guest(guestname, username, password, logger)
        # username: root
        user_code_1 = [19, 24]
        domobj.sendKey(0, 30, user_code_1, len(user_code_1), 0)
        user_code_2 = [24, 20, 28]
        domobj.sendKey(0, 30, user_code_2, len(user_code_2), 0)
        time.sleep(2)
        # password: redhat
        passwd_code = [19, 18, 32, 35, 30, 20, 28]
        domobj.sendKey(0, 30, passwd_code, len(passwd_code), 0)
        time.sleep(3)
        if clean_guest(domobj, logger, username, password, ip):
            logger.error("clean guest failed.")
            return 1

        time.sleep(5)
        if codeset == "atset2" or codeset == "atset3":
            logger.info("send key to guest: %s" % KEYCODE_2)
            domobj.sendKey(codeset_value, 30, KEYCODE_2, len(KEYCODE_2), 0)
        elif codeset == "osx":
            logger.info("send key to guest: %s" % KEYCODE_3)
            domobj.sendKey(codeset_value, 30, KEYCODE_3, len(KEYCODE_3), 0)
        elif codeset == "win32":
            logger.info("send key to guest: %s" % KEYCODE_4)
            domobj.sendKey(codeset_value, 30, KEYCODE_4, len(KEYCODE_4), 0)
        elif codeset == "usb":
            logger.info("send key to guest: %s" % KEYCODE_5)
            domobj.sendKey(codeset_value, 30, KEYCODE_5, len(KEYCODE_5), 0)
            domobj.sendKey(codeset_value, 30, KEYCODE_5, len(KEYCODE_5), 0)
        else:
            logger.info("send key to guest: %s" % KEYCODE_1)
            domobj.sendKey(codeset_value, 30, KEYCODE_1, len(KEYCODE_1), 0)
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("fail to sendkey domain")
        return 1

    time.sleep(20)
    if check_file(domobj, logger, username, password, ip):
        logger.error("FAIL: send key to guest failed")
        return 1

    if clean_guest(domobj, logger, username, password, ip):
        logger.error("clean guest failed.")
        return 1

    logger.info("PASS: send key to guest successfully")
    return 0
