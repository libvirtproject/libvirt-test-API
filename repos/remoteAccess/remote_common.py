#!/usr/bin/evn python

from utils import utils


def stop_remote_libvirtd(target_machine, username, password, logger):
    cmd = "systemctl stop libvirtd"
    ret, output = utils.remote_exec_pexpect(target_machine, username, password, cmd)
    if ret:
        logger.error("Failed to stop libvirtd: %s" % output)
        return 1
    cmd = "systemctl stop libvirtd.socket libvirtd-admin.socket libvirtd-ro.socket libvirtd-tcp.socket libvirtd-tls.socket"
    ret, output = utils.remote_exec_pexpect(target_machine, username, password, cmd)
    if ret:
        logger.error("Failed to stop socket: %s" % output)
        return 1
    cmd = "systemctl mask libvirtd.socket libvirtd-admin.socket libvirtd-ro.socket libvirtd-tcp.socket libvirtd-tls.socket"
    ret, output = utils.remote_exec_pexpect(target_machine, username, password, cmd)
    if ret:
        logger.error("Failed to mask socket: %s" % output)
        return 1
