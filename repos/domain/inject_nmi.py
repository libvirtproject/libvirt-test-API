#!/usr/bin/env python

from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('guestname',)
optional_params = {}

USER = "root"
PASSWD = "redhat"
NMI_INFO = "NMI received for unknown reason"


def check_rsyslog(ip, logger):
    cmd = "rpm -qa | grep rsyslog"
    ret, out = utils.remote_exec_pexpect(ip, USER, PASSWD, cmd)
    if ret:
        cmd = "yum install rsyslog -y"
        ret, out = utils.remote_exec_pexpect(ip, USER, PASSWD, cmd)
        if ret:
            logger.error("out: %s" % out)
            return 1
    cmd = "systemctl restart rsyslog.service"
    ret, out = utils.remote_exec_pexpect(ip, USER, PASSWD, cmd)
    if ret:
        logger.error("out: %s" % out)
        return 1
    return 0


def inject_nmi(params):
    guestname = params['guestname']
    logger = params['logger']

    if utils.isPower():
        logger.info("Don't support injectNMI() on ppc machine.")
        return 0

    try:
        conn = sharedmod.libvirtobj['conn']
        domobj = conn.lookupByName(guestname)
        mac = utils.get_dom_mac_addr(guestname)
        ip = utils.mac_to_ip(mac, 120)
        if check_rsyslog(ip, logger):
            return 1
        logger.info('inject NMI to domain.')
        domobj.injectNMI()
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("inject NMI failed.")
        return 1

    cmd = "grep '%s' /var/log/messages" % NMI_INFO
    logger.debug("cmd: %s" % cmd)
    ret, out = utils.remote_exec_pexpect(ip, USER, PASSWD, cmd)
    if ret:
        logger.error("FAIL: inject NMI to guest failed.")
        logger.error("out : %s" % out)
        return 1

    logger.info("PASS: inject NMI to guest successful.")
    return 0
