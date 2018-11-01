"""
NFS server set up and mount.
"""
import re
import os
import shutil

from utils import process
from . import utils


def local_nfs_exported(nfs_path):
    cmd = "exportfs -o rw,no_root_squash *:%s" % nfs_path
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("%s failed: %s." % (cmd, ret.stdout))
        return False
    return True

def local_nfs_exported_clean(nfs_path):
    cmd = "exportfs -u *:%s" % nfs_path
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("%s failed: %s." % (cmd, ret.stdout))
        return False
    return True


def local_restart_service(logger):
    if utils.isRelease("8", logger):
        cmd = "systemctl restart nfs-server"
    else:
        cmd = "systemctl restart nfs"
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("start nfs service failed: %s." % ret.stdout)
        return False
    cmd = "systemctl restart rpcbind"
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("start rpcbind service failed: %s." % ret.stdout)
        return False
    return True


def local_is_mounted(nfs_path, mount_path, logger):
    cmd = "cat /proc/mounts"
    ret = process.system_output(cmd, shell=True, ignore_status=True)
    for line in ret.splitlines():
        if nfs_path in line and mount_path in line:
            logger.info("%s is mounted." % nfs_path)
            return True
    return False


def local_mount(nfs_path, mount_path, logger):
    if local_is_mounted(nfs_path, mount_path, logger):
        local_umount(mount_path, logger)
    options = "-o rw"
    cmd = "mount %s -t nfs %s %s" % (options, nfs_path, mount_path)
    ret = process.run(cmd, shell=True)
    if ret.exit_status:
        logger.error("mount %s failed: %s" % (nfs_path, ret.stdout))
        return False
    return True


def local_umount(mount_path, logger):
    cmd = "umount -lf %s" % mount_path
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("%s failed: %s." % (cmd, ret.stdout))
        return False
    return True


def local_nfs_setup(nfs_path, mount_path, logger):
    local_restart_service(logger)
    if local_is_mounted(nfs_path, mount_path, logger):
        local_umount(mount_path, logger)
    if not os.path.exists(nfs_path):
        logger.info("%s is not exist." % nfs_path)
        os.makedirs(nfs_path)
    if not os.path.exists(mount_path):
        logger.info("%s is not exist." % mount_path)
        os.makedirs(mount_path)
    if os.path.exists(mount_path) and not os.path.isdir(mount_path):
        logger.error("%s is not a directory." % mount_path)
        return False
    local_nfs_exported(nfs_path)
    local_mount("127.0.0.1:" + nfs_path, mount_path, logger)
    return True


def local_nfs_clean(nfs_path, mount_path, logger):
    local_umount(mount_path, logger)
    if os.path.exists(nfs_path):
        local_nfs_exported_clean(nfs_path)
        shutil.rmtree(nfs_path)
    local_restart_service(logger)
    return True


def remote_is_mounted(remote_ip, username, password, nfs_path, mount_path, logger):
    cmd = "cat /proc/mounts"
    ret, out = utils.remote_exec_pexpect(remote_ip, username, password, cmd)
    for line in out.splitlines():
        if nfs_path in line and mount_path in line:
            logger.info("remote %s is mounted." % nfs_path)
            return True
    return False


def remote_mount(server_ip, remote_ip, username, password, nfs_path, mount_path, logger):
    if remote_is_mounted(remote_ip, username, password, nfs_path, mount_path, logger):
        remote_umount(remote_ip, username, password, mount_path, logger)
    cmd = "ls %s" % mount_path
    ret, out = utils.remote_exec_pexpect(remote_ip, username, password, cmd)
    if ret:
        cmd = "mkdir -p %s" % mount_path
        ret, out = utils.remote_exec_pexpect(remote_ip, username, password, cmd)
        if ret:
            logger.error("%s failed: %s" % (cmd, out))
            return False
    options = "-o rw"
    cmd = "mount %s -t nfs %s:%s %s" % (options, server_ip, nfs_path, mount_path)
    ret, out = utils.remote_exec_pexpect(remote_ip, username, password, cmd)
    if ret:
        logger.error("remote mount %s failed: %s" % (nfs_path, out))
        return False
    return True


def remote_umount(remote_ip, username, password, mount_path, logger):
    cmd = "umount -lf %s" % mount_path
    ret, out = utils.remote_exec_pexpect(remote_ip, username, password, cmd)
    if ret:
        logger.error("remote %s failed: %s." % (cmd, out))
        return False
    return True


def nfs_setup(server_ip, remote_ip, username, password, nfs_path, mount_path, logger):
    if not local_nfs_setup(nfs_path, mount_path, logger):
        logger.error("nfs server setup failed.")
        return False
    cmd = "setsebool virt_use_nfs 1 -P"
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("%s failed: %s." % (cmd, ret.stdout))
        return False

    if remote_ip is not None:
        if not remote_mount(server_ip, remote_ip, username, password, nfs_path, mount_path, logger):
            logger.error("remote mount failed.")
            return False
        cmd = "setsebool virt_use_nfs 1 -P"
        ret, out = utils.remote_exec_pexpect(remote_ip, username, password, cmd)
        if ret:
            logger.error("%s failed: %s." % (cmd, out))
            return False
    return True


def nfs_clean(remote_ip, username, password, nfs_path, mount_path, logger):
    if not local_nfs_clean(nfs_path, mount_path, logger):
        logger.error("nfs server clean failed.")
        return False
    if remote_ip is not None:
        if not remote_umount(remote_ip, username, password, mount_path, logger):
            logger.error("remote umount failed.")
            return False
    return True
