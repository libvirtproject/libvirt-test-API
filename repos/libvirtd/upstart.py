#!/usr/bin/env python
# Upstart libvirtd testing
#
# NOTES: Libvirtd will be restarted during test, better run this
# case alone.

import os
import time

from utils import utils
from shutil import copy

required_params = ()
optional_params = {}

VIRSH_LIST = "virsh list --all"
UPSTART_CONF = "rpm -ql libvirt|grep upstart"
INITCTL_CMD = "/sbin/initctl"
SYSTEMCTL_CMD = "/bin/systemctl"
INITCTL_RELOAD_CMD = "initctl reload-configuration"
SYSTEMCTL_RELOAD_CMD = "systemctl daemon-reload"
INIT_CONF = "/etc/init/libvirtd.conf"


def libvirtd_check(logger):
    """check libvirtd status
    """
    cmd = "service libvirtd status"
    ret, out = utils.exec_cmd(cmd, shell=True)
    if ret != 0:
        logger.error("failed to get libvirtd status")
        return 1
    else:
        logger.info(out)

    logger.info(VIRSH_LIST)
    ret, out = utils.exec_cmd(VIRSH_LIST, shell=True)
    if ret != 0:
        logger.error("failed to get virsh list result")
        return 1
    else:
        for i in range(len(out)):
            logger.info(out)

    return 0


def upstart(params):
    """Set libvirtd upstart"""
    logger = params['logger']

    logger.info("chkconfig libvirtd off:")
    cmd = "chkconfig libvirtd off"
    ret, out = utils.exec_cmd(cmd, shell=True)
    if ret != 0:
        logger.error("failed")
        return 1
    else:
        logger.info("succeed")

    cmd = "service libvirtd stop"
    logger.info(cmd)
    ret, out = utils.exec_cmd(cmd, shell=True)
    if ret != 0:
        logger.error("failed to stop libvirtd service")
        return 1
    else:
        logger.info(str(out))

    if os.path.exists(SYSTEMCTL_CMD):
        logger.info(SYSTEMCTL_RELOAD_CMD)
        ret, out = utils.exec_cmd(SYSTEMCTL_RELOAD_CMD, shell=True)
        if ret != 0:
            logger.error("failed to reload systemd manager configuration")
            return 1
        else:
            logger.info("succeed")

        cmd = "systemctl start libvirtd.service"
        logger.info(cmd)
        ret, out = utils.exec_cmd(cmd, shell=True)
        if ret != 0:
            logger.error("failed to start libvirtd.service by systemctl")
            return 1
        else:
            logger.info(out)

        cmd = "systemctl status libvirtd.service"
        logger.info("get libvirtd.service status by systemctl:")
        ret, out = utils.exec_cmd(cmd, shell=True)
        if ret != 0:
            logger.info("failed to get libvirtd.service status by systemctl")
            return 1
        else:
            logger.info(out)

    elif os.path.exists(INITCTL_CMD):
        logger.info("find libvirtd.upstart file in libvirt package:")
        ret, conf = utils.exec_cmd(UPSTART_CONF, shell=True)
        if ret != 0:
            logger.error("can't find libvirtd.upstart as part of libvirt package")
            return 1
        elif conf[0]:
            logger.info("succeed")
            logger.info("copy %s to %s" % (conf[0], INIT_CONF))
            copy(conf[0], INIT_CONF)

        logger.info(INITCTL_RELOAD_CMD)
        ret, out = utils.exec_cmd(INITCTL_RELOAD_CMD, shell=True)
        if ret != 0:
            logger.error("failed to reload configuration")
            return 1
        else:
            logger.info("succeed")

        cmd = "initctl start libvirtd"
        logger.info(cmd)
        ret, out = utils.exec_cmd(cmd, shell=True)
        if ret != 0:
            logger.error("failed to start libvirtd by initctl")
            return 1
        else:
            logger.info(out)

        cmd = "initctl status libvirtd"
        logger.info("get libvirtd status by initctl:")
        ret, out = utils.exec_cmd(cmd, shell=True)
        if ret != 0:
            logger.info("failed to get libvirtd status by initctl")
            return 1
        else:
            logger.info(out)

    else:
        return 1

    time.sleep(5)

    logger.info("check the libvirtd status:")
    ret = libvirtd_check(logger)
    if ret:
        return 1

    cmd = "killall -9 libvirtd"
    logger.info("kill libvirtd process")
    ret, out = utils.exec_cmd(cmd, shell=True)
    if ret != 0:
        logger.error("failed to kill libvirtd process")
        return 1
    else:
        logger.info("succeed")

    time.sleep(5)

    logger.info("recheck libvirtd status:")
    ret = libvirtd_check(logger)
    if ret:
        time.sleep(1)
        return 1
    else:
        logger.info("the libvirtd process successfully restarted after kill")
        time.sleep(1)

    return 0


def upstart_clean(params):
    """clean testing environment"""
    logger = params['logger']

    if os.path.exists(INITCTL_CMD):
        cmd = "initctl stop libvirtd"
        ret, out = utils.exec_cmd(cmd, shell=True)
        if ret != 0:
            logger.error("failed to stop libvirtd by initctl")

        if os.path.exists(INIT_CONF):
            os.remove(INIT_CONF)

        ret, out = utils.exec_cmd(INITCTL_RELOAD_CMD, shell=True)
        if ret != 0:
            logger.error("failed to reload init confituration")

    elif os.path.exists(SYSTEMCTL_CMD):
        cmd = "systemctl stop libvirtd.service"
        ret, out = utils.exec_cmd(cmd, shell=True)
        if ret != 0:
            logger.error("failed to stop libvirtd.service by systemctl")

        if os.path.exists(INIT_CONF):
            os.remove(INIT_CONF)

        ret, out = utils.exec_cmd(SYSTEMCTL_RELOAD_CMD, shell=True)
        if ret != 0:
            logger.error("failed to reload systemd manager confituration")

    cmd = "service libvirtd restart"
    ret, out = utils.exec_cmd(cmd, shell=True)
    if ret != 0:
        logger.error("failed to restart libvirtd")

    cmd = "chkconfig --level 345 libvirtd on"
    ret, out = utils.exec_cmd(cmd, shell=True)
    if ret != 0:
        logger.error("failed to set chkconfig")
