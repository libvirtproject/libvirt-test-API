#!/usr/bin/evn python

import libvirt
import pexpect
import string

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
