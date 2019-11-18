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


def restart_remote_libvirtd(target_machine, username, password, logger, socket_type=None):
    # From libvirt-5.6.0, libvirtd is using systemd socket activation by default.
    # So need to restart remote libvirtd socket.
    if utils.version_compare('libvirt-python', 5, 6, 0, logger) and socket_type:
        logger.info("Restart libvirtd-%s.socket." % socket_type)
        cmd = "systemctl stop libvirtd; systemctl restart libvirtd-%s.socket" % socket_type
        ret, output = utils.remote_exec_pexpect(target_machine, username,
                                                password, cmd)
        if ret:
            logger.error("Fail to restart libvirtd-%s.socket." % socket_type)
            return 1
    # Restart remote libvirtd service
    cmd = "service libvirtd restart"
    logger.info("Restart libvirtd.")
    ret, output = utils.remote_exec_pexpect(target_machine, username,
                                            password, cmd)
    if ret:
        logger.error("Failed to restart libvirtd service.")
        return 1
    return 0


def set_firewall(port, target_machine, username, password, logger):
    cmd = "firewall-cmd --add-port=%s --permanent --zone=public;firewall-cmd --reload" % port
    logger.info("cmd: %s" % cmd)
    ret, output = utils.remote_exec_pexpect(target_machine, username,
                                            password, cmd)
    if ret:
        logger.error("Failed to set firewall.")
        return 1
    return 0
