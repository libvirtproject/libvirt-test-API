#!/usr/bin/evn python

import libvirt
import pexpect
import string
import time

from utils import utils

SSH_KEYGEN = "ssh-keygen -t rsa"
SSH_COPY_ID = "ssh-copy-id"


def ssh_keygen(logger):
    """using pexpect to generate RSA"""
    logger.info("generate ssh RSA \"%s\"" % SSH_KEYGEN)
    child = pexpect.spawn(SSH_KEYGEN)
    while True:
        index = child.expect([
                             'Enter file in which to save the key ',
                             'Enter passphrase ',
                             'Enter same passphrase again: ',
                             pexpect.EOF,
                             pexpect.TIMEOUT])
        if index == 0:
            child.sendline("\r")
        elif index == 1:
            child.sendline("\r")
        elif index == 2:
            child.sendline("\r")
        elif index == 3:
            logger.debug(string.strip(child.before))
            child.close()
            return 0
        elif index == 4:
            logger.error("ssh_keygen timeout")
            logger.debug(string.strip(child.before))
            child.close()
            return 1

    return 0


def ssh_tunnel(hostname, username, password, logger):
    """setup a tunnel to a give host"""
    logger.info("setup ssh tunnel with host %s" % hostname)
    user_host = "%s@%s" % (username, hostname)
    child = pexpect.spawn(SSH_COPY_ID, [user_host])
    while True:
        index = child.expect(['yes\/no', 'password: ',
                             pexpect.EOF,
                             pexpect.TIMEOUT])
        if index == 0:
            child.sendline("yes")
        elif index == 1:
            child.sendline(password)
        elif index == 2:
            logger.debug(string.strip(child.before))
            child.close()
            return 0
        elif index == 3:
            logger.error("setup tunnel timeout")
            logger.debug(string.strip(child.before))
            child.close()
            return 1

    return 0


def request_credentials(credentials, user_data):
    for credential in credentials:
        if credential[0] == libvirt.VIR_CRED_AUTHNAME:
            credential[4] = user_data[0]

            if len(credential[4]) == 0:
                credential[4] = credential[3]
        elif credential[0] == libvirt.VIR_CRED_PASSPHRASE:
            credential[4] = user_data[1]
        else:
            return -1

    return 0


def get_flags(params, logger):
    flags = params['flags']
    if flags == 'none':
        return 0
    ret = 0
    for flag in flags.split('|'):
        if flag == 'running':
            ret |= libvirt.VIR_DOMAIN_SAVE_RUNNING
        elif flag == 'paused':
            ret |= libvirt.VIR_DOMAIN_SAVE_PAUSED
        elif flag == 'bypass-cache':
            ret |= libvirt.VIR_DOMAIN_SAVE_BYPASS_CACHE
        else:
            logger.error("Flags error:illegal flags %s" % flags)
            return -1
    return ret


def get_fileflags(filepath, fileflags, fdinfo, logger):
    """Get the file flags of file"""
    CHECK_CMD = "lsof -w %s | awk '/libvirt_i/{print $2}'" % filepath

    # For dump/save/managedsave, fdinfo is 1
    # For start/restore, fdinfo is 0
    GET_CMD = "cat /proc/%s/fdinfo/%s |grep flags|awk '{print $NF}'"

    timeout = 100
    while True:
        (status, pid) = utils.exec_cmd(CHECK_CMD, shell=True)
        if status == 0 and len(pid) == 1:
            break
        time.sleep(0.1)
        timeout -= 0.1
        if timeout <= 0:
            logger.error("Timeout waiting for file to show up.")
            return 1

    (status, output) = utils.exec_cmd(GET_CMD % (pid[0], fdinfo), shell=True)
    if status == 0 and len(output) == 1:
        logger.info("The flags of file %s " % output[0])
        fileflags.append(output[0])
    else:
        logger.error("Fail to get the file flags")
        return 1


def check_fileflag(fileflags, expect_flag, logger):
    """Check the file flags """
    if fileflags == expect_flag:
        logger.info("file flags include %s." % expect_flag)
        return True
    else:
        logger.error("file flags doesn't include %s." % expect_flag)
        return False


def check_dom_state(domobj):
    state = domobj.info()[0]
    expect_states = [libvirt.VIR_DOMAIN_PAUSED, libvirt.VIR_DOMAIN_RUNNING]
    if state in expect_states:
        return state
    return -1
