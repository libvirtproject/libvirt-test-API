#!/usr/bin/env python

import os
import re
import sys
import pexpect
import string
import commands

import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ('transport',
                   'target_machine',
                   'username',
                   'password',
                   'guestname',
                   'prestate',
                   'poststate',
                   'presrcconfig',
                   'postsrcconfig',
                   'predstconfig',
                   'postdstconfig',
                   'flags',)
optional_params = {}

SSH_KEYGEN = "ssh-keygen -t rsa"
SSH_COPY_ID = "ssh-copy-id"


def get_state(state):
    dom_state = ''
    if state == libvirt.VIR_DOMAIN_NOSTATE:
        dom_state = 'nostate'
    elif state == libvirt.VIR_DOMAIN_RUNNING:
        dom_state = 'running'
    elif state == libvirt.VIR_DOMAIN_BLOCKED:
        dom_state = 'blocked'
    elif state == libvirt.VIR_DOMAIN_PAUSED:
        dom_state = 'paused'
    elif state == libvirt.VIR_DOMAIN_SHUTDOWN:
        dom_state = 'shutdown'
    elif state == libvirt.VIR_DOMAIN_SHUTOFF:
        dom_state = 'shutoff'
    elif state == libvirt.VIR_DOMAIN_CRASHED:
        dom_state = 'crashed'
    else:
        dom_state = 'no sure'
    return dom_state


def exec_command(logger, command, flag):
    """execute shell command
    """
    status, ret = commands.getstatusoutput(command)
    if not flag and status:
        logger.error("executing " + "\"" + command + "\"" + " failed")
        logger.error(ret)
    return status, ret


def env_clean(srcconn, dstconn, target_machine, guestname, logger):

    logger.info("destroy and undefine %s on both side if it exsits", guestname)
    exec_command(logger, "virsh destroy %s" % guestname, 1)
    exec_command(logger, "virsh undefine %s" % guestname, 1)
    REMOTE_DESTROY = "ssh %s \"virsh destroy %s\"" % (
        target_machine, guestname)
    exec_command(logger, REMOTE_DESTROY, 1)
    REMOTE_UNDEFINE = "ssh %s \"virsh undefine %s\"" % (
        target_machine, guestname)
    exec_command(logger, REMOTE_UNDEFINE, 1)

    dstconn.close()
    logger.info("close remote hypervisor connection")

    REMOVE_SSH = "ssh %s \"rm -rf /root/.ssh/*\"" % (target_machine)
    logger.info("remove ssh key on remote machine")
    status, ret = exec_command(logger, REMOVE_SSH, 0)
    if status:
        logger.error("failed to remove ssh key")

    REMOVE_LOCAL_SSH = "rm -rf /root/.ssh/*"
    logger.info("remove local ssh key")
    status, ret = exec_command(logger, REMOVE_LOCAL_SSH, 0)
    if status:
        logger.error("failed to remove local ssh key")


def ssh_keygen(logger):
    """using pexpect to generate RSA"""
    logger.info("generate ssh RSA \"%s\"" % SSH_KEYGEN)
    child = pexpect.spawn(SSH_KEYGEN)
    while True:
        index = child.expect(['Enter file in which to save the key ',
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


def migrate(params):
    """ migrate a guest back and forth between two machines"""
    logger = params['logger']

    transport = params['transport']
    target_machine = params['target_machine']
    username = params['username']
    password = params['password']
    guestname = params['guestname']
    poststate = params['poststate']
    presrcconfig = params['presrcconfig']
    postsrcconfig = params['postsrcconfig']
    predstconfig = params['predstconfig']
    postdstconfig = params['postdstconfig']
    flags = params['flags']

    logger.info("the flags is %s" % flags)
    flags_string = flags.split("|")

    migflags = 0
    for flag in flags_string:
        if flag == '0':
            migflags |= 0
        elif flag == 'peer2peer':
            migflags |= libvirt.VIR_MIGRATE_PEER2PEER
        elif flag == 'tunnelled':
            migflags |= libvirt.VIR_MIGRATE_TUNNELLED
        elif flag == 'live':
            migflags |= libvirt.VIR_MIGRATE_LIVE
        elif flag == 'persist_dest':
            migflags |= libvirt.VIR_MIGRATE_PERSIST_DEST
        elif flag == 'undefine_source':
            migflags |= libvirt.VIR_MIGRATE_UNDEFINE_SOURCE
        elif flag == 'paused':
            migflags |= libvirt.VIR_MIGRATE_PAUSED
        else:
            logger.error("unknown flag")
            return 1

    # generate ssh key pair
    ret = ssh_keygen(logger)
    if ret:
        logger.error("failed to generate RSA key")
        return 1
    # setup ssh tunnel with target machine
    ret = ssh_tunnel(target_machine, username, password, logger)
    if ret:
        logger.error(
            "faild to setup ssh tunnel with target machine %s" %
            target_machine)
        return 1

    commands.getstatusoutput("ssh-add")

    dsturi = "qemu+%s://%s/system" % (transport, target_machine)

    # Connect to local hypervisor connection URI
    srcconn = sharedmod.libvirtobj['conn']
    dstconn = libvirt.open(dsturi)

    srcdom = srcconn.lookupByName(guestname)

    if predstconfig == "true":
        guest_names = dstconn.listDefinedDomains()
        if guestname in guest_names:
            logger.info("Dst VM exists")
        else:
            logger.error(
                "Dst VM missing config, should define VM on Dst first")
            env_clean(srcconn, dstconn, target_machine, guestname, logger)
            return 1

    try:
        if(migflags & libvirt.VIR_MIGRATE_PEER2PEER):
            logger.info("use migrate_to_uri() API to migrate")
            srcdom.migrateToURI(dsturi, migflags, None, 0)
        else:
            logger.info("use migrate() to migrate")
            srcdom.migrate(dstconn, migflags, None, None, 0)
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        logger.error("Migration Failed")
        env_clean(srcconn, dstconn, target_machine, guestname, logger)
        return 1

    if postsrcconfig == "true":
        if srcdom.isActive():
            logger.error("Source VM is still active")
            env_clean(srcconn, dstconn, target_machine, guestname, logger)
            return 1
        if not srcdom.isPersistent():
            logger.error("Source VM missing config")
            env_clean(srcconn, dstconn, target_machine, guestname, logger)
            return 1
    else:
        guest_names = []
        ids = srcconn.listDomainsID()
        for id in ids:
            obj = srcconn.lookupByID(id)
            guest_names.append(obj.name())
        guest_names += srcconn.listDefinedDomains()

        if guestname in guest_names:
            logger.error("Source VM still exists")
            env_clean(srcconn, dstconn, target_machine, guestname, logger)
            return 1

    dstdom = dstconn.lookupByName(guestname)
    if not dstdom.isActive():
        logger.error("Dst VM is not active")
        env_clean(srcconn, dstconn, target_machine, guestname, logger)
        return 1

    if postdstconfig == "true":
        if not dstdom.isPersistent():
            logger.error("Dst VM missing config")
            env_clean(srcconn, dstconn, target_machine, guestname, logger)
            return 1

    dstdom_state = dstdom.info()[0]
    if get_state(dstdom_state) != poststate:
        logger.error(
            "Dst VM wrong state %s, should be %s",
            get_state(dstdom_state),
            poststate)
        env_clean(srcconn, dstconn, target_machine, guestname, logger)
        return 1

    logger.info("Migration PASS")
    env_clean(srcconn, dstconn, target_machine, guestname, logger)
    return 0
