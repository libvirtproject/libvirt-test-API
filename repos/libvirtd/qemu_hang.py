#!/usr/bin/env python
# QEMU get hang should not cause libvirtd hang or dead. This
# test stop a qemu process and check whether libvird get hang.
# For doing this test, a running domain is required.


from src import sharedmod
from utils import utils

required_params = ('guestname',)
optional_params = {}

VIRSH_LIST = "virsh list --all"


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


def libvirtd_check(logger):
    """check libvirtd status
    """
    cmd = "service libvirtd status"
    ret, out = utils.exec_cmd(cmd, shell=True)
    if ret != 0:
        logger.error("failed to get libvirtd status")
        return 1
    else:
        logger.info(out[0])

    logger.info(VIRSH_LIST)
    ret, out = utils.exec_cmd(VIRSH_LIST, shell=True)
    if ret != 0:
        logger.error("failed to get virsh list result")
        return 1
    else:
        for i in range(len(out)):
            logger.info(out[i])

    return 0


def get_domain_pid(logger, guestname):
    """get the pid of running domain"""
    logger.info("get the pid of running domain %s" % guestname)
    get_pid_cmd = "cat /var/run/libvirt/qemu/%s.pid" % guestname
    ret, pid = utils.exec_cmd(get_pid_cmd, shell=True)
    if ret:
        logger.error("fail to get the pid of runnings domain %s" %
                     guestname)
        return 1, ""
    else:
        logger.info("the pid of domain %s is %s" %
                    (guestname, pid[0]))
        return 0, pid[0]


def qemu_hang(params):
    """Hang qemu process, check libvirtd status"""
    logger = params['logger']
    guestname = params['guestname']

    conn = sharedmod.libvirtobj['conn']

    logger.info("check the domain state")
    ret = check_domain_running(conn, guestname, logger)
    if ret:
        return 1

    logger.info("check the libvirtd status:")
    ret = libvirtd_check(logger)
    if ret:
        return 1

    ret, pid = get_domain_pid(logger, guestname)
    if ret:
        return 1

    cmd = "kill -STOP %s" % pid
    logger.info(cmd)
    ret, out = utils.exec_cmd(cmd, shell=True)
    if ret:
        logger.error("failed to stop qemu process of %s" % guestname)
        return 1

    logger.info("recheck libvirtd status:")
    ret = libvirtd_check(logger)
    if ret:
        return 1

    return 0


def qemu_hang_clean(params):
    """ clean testing environment """
    logger = params['logger']
    guestname = params['guestname']

    ret = get_domain_pid(logger, guestname)
    cmd = "kill -CONT %s" % ret[1]
    ret = utils.exec_cmd(cmd, shell=True)
    if ret[0]:
        logger.error("failed to resume qemu process of %s" % guestname)

    return 0
