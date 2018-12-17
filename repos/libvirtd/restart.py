#!/usr/bin/evn python
# Restart libvirtd testing. A running guest is required in
# this test. During libvirtd restart, the guest remains
# running and not affected by libvirtd restart.
#
# NOTES: Libvirtd will be restarted during test, better run this
# case alone.

from src import sharedmod
from utils import utils

required_params = ()
optional_params = {'guestname': ''}

VIRSH_LIST = "virsh list --all"
RESTART_CMD = "service libvirtd restart"


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


def restart(params):
    """restart libvirtd test"""
    logger = params['logger']
    guestname = params.get('guestname', '')

    conn = sharedmod.libvirtobj['conn']

    logger.info("check the libvirtd status:")
    ret = libvirtd_check(logger)
    if ret:
        return 1

    if guestname != '':
        logger.info("check the domain state")
        ret = check_domain_running(conn, guestname, logger)
        if ret:
            return 1

        # Get domain ip
        logger.info("get the mac address of domain %s" % guestname)
        mac = utils.get_dom_mac_addr(guestname)
        logger.info("the mac address of domain %s is %s" % (guestname, mac))
        logger.info("get ip by mac address")
        ip = utils.mac_to_ip(mac, 180)
        logger.info("the ip address of domain %s is %s" % (guestname, ip))

        logger.info("ping to domain %s" % guestname)
        if utils.do_ping(ip, 0):
            logger.info("Success ping domain %s" % guestname)
        else:
            logger.error("fail to ping domain %s" % guestname)
            return 1

        ret, pid_before = get_domain_pid(logger, guestname)
        if ret:
            return 1

    logger.info("restart libvirtd service:")
    ret, out = utils.exec_cmd(RESTART_CMD, shell=True)
    if ret != 0:
        logger.error("failed to restart libvirtd")
        for i in range(len(out)):
            logger.error(out[i])
        return 1
    else:
        for i in range(len(out)):
            logger.info(out[i])

    logger.info("recheck libvirtd status:")
    ret = libvirtd_check(logger)
    if ret:
        return 1

    if guestname != '':
        logger.info("ping to domain %s again" % guestname)
        if utils.do_ping(ip, 0):
            logger.info("Success ping domain %s" % guestname)
        else:
            logger.error("fail to ping domain %s" % guestname)
            return 1

        ret, pid_after = get_domain_pid(logger, guestname)
        if ret:
            return 1

        if pid_before != pid_after:
            logger.error("%s pid changed during libvirtd restart" %
                         guestname)
            return 1
        else:
            logger.info("domain pid not change, %s keeps running during \
                         libvirtd restart" % guestname)

    return 0
