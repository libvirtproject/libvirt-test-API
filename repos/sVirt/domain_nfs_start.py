#!/usr/bin/env python
# This test is for start a guest with img file on nfs storage.
# Under SElinux boolean virt_use_nfs on or off, combine with
# setting the dynamic_ownership in /etc/libvirt/qemu.conf,
# check whether the guest can be started or not. The nfs could
# be root_squash or no_root_squash. SElinux should be enabled
# and enforcing on host.
#
# NOTES: Libvirtd will be restarted during test, better run this
# case alone.

import os
import re
import sys

import libvirt
from libvirt import libvirtError
from src import sharedmod
from utils import utils
from shutil import copy

required_params = ('guestname',
                   'dynamic_ownership',
                   'virt_use_nfs',
                   'root_squash',)
optional_params = {}

QEMU_CONF = "/etc/libvirt/qemu.conf"


def nfs_setup(root_squash, logger):
    """setup nfs on localhost
    """
    logger.info("set nfs service")
    if root_squash == "yes":
        option = "root_squash"
    elif root_squash == "no":
        option = "no_root_squash"
    else:
        logger.error("wrong root_squash value")
        return 1

    cmd = "echo /tmp *\(rw,%s\) >> /etc/exports" % option
    ret, out = utils.exec_cmd(cmd, shell=True)
    if ret:
        logger.error("failed to config nfs export")
        return 1

    logger.info("restart nfs service")
    cmd = "service nfs restart"
    ret, out = utils.exec_cmd(cmd, shell=True)
    if ret:
        logger.error("failed to restart nfs service")
        return 1
    else:
        for i in range(len(out)):
            logger.info(out[i])

    return 0


def prepare_env(d_ownership, virt_use_nfs, guestname, root_squash,
                disk_file, img_dir, logger):
    """set virt_use_nfs SElinux boolean, configure
       dynamic_ownership in /etc/libvirt/qemu.conf
    """
    logger.info("set virt_use_nfs selinux boolean")
    cmd = "setsebool virt_use_nfs %s" % virt_use_nfs
    ret, out = utils.exec_cmd(cmd, shell=True)
    if ret:
        logger.error("failed to set virt_use_nfs SElinux boolean")
        return 1

    logger.info("set the dynamic ownership in %s as %s" %
                (QEMU_CONF, d_ownership))
    if d_ownership == "enable":
        option = 1
    elif d_ownership == "disable":
        option = 0
    else:
        logger.error("wrong dynamic_ownership value")
        return 1

    set_cmd = "echo dynamic_ownership = %s >> %s" % \
        (option, QEMU_CONF)
    ret, out = utils.exec_cmd(set_cmd, shell=True)
    if ret:
        logger.error("failed to set dynamic ownership")
        return 1

    logger.info("restart libvirtd")
    restart_cmd = "service libvirtd restart"
    ret, out = utils.exec_cmd(restart_cmd, shell=True)
    if ret:
        logger.error("failed to restart libvirtd")
        for i in range(len(out)):
            logger.info(out[i])
        return 1
    else:
        for i in range(len(out)):
            logger.info(out[i])

    file_name = os.path.basename(disk_file)
    filepath = "/tmp/%s" % file_name
    if os.path.exists(filepath):
        os.remove(filepath)

    logger.info("copy %s img file to nfs path" % guestname)
    copy(disk_file, "/tmp")

    logger.info("set up nfs service on localhost")
    ret = nfs_setup(root_squash, logger)
    if ret:
        return 1

    logger.info("mount nfs to img dir path")
    mount_cmd = "mount -o vers=3 127.0.0.1:/tmp %s" % img_dir
    ret, out = utils.exec_cmd(mount_cmd, shell=True)
    if ret:
        logger.error("Failed to mount the nfs path")
        for i in range(len(out)):
            logger.info(out[i])
        return 1

    return 0


def domain_nfs_start(params):
    """start domain with img on nfs"""
    logger = params['logger']
    guestname = params['guestname']
    dynamic_ownership = params['dynamic_ownership']
    virt_use_nfs = params['virt_use_nfs']
    root_squash = params['root_squash']

    conn = sharedmod.libvirtobj['conn']
    domobj = conn.lookupByName(guestname)

    logger.info("get the domain state")
    try:
        state = domobj.info()[0]
        logger.info("domain %s is %s" % (guestname, state))
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("Error: fail to get domain %s state" % guestname)
        return 1

    if state != libvirt.VIR_DOMAIN_SHUTOFF:
        logger.info("shut down the domain %s" % guestname)
        try:
            domobj.destroy()
        except libvirtError as e:
            logger.error("API error message: %s, error code is %s"
                         % (e.get_error_message(), e.get_error_code()))
            logger.error("Error: fail to destroy domain %s" % guestname)
            return 1

    logger.info("get guest img file path")
    try:
        dom_xml = domobj.XMLDesc(0)
        disk_file = utils.get_disk_path(dom_xml)
        logger.info("%s disk file path is %s" % (guestname, disk_file))
        img_dir = os.path.dirname(disk_file)
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("Error: fail to get domain %s xml" % guestname)
        return 1

    # set env
    logger.info("prepare the environment")
    ret = prepare_env(dynamic_ownership, virt_use_nfs, guestname,
                      root_squash, disk_file, img_dir, logger)
    if ret:
        logger.error("failed to prepare the environment")
        return 1

    # reconnect libvirt
    conn = utils.get_conn()

    domobj = conn.lookupByName(guestname)

    logger.info("begin to test start domain from nfs storage")
    logger.info("First, start the domain without chown the img file to qemu")
    logger.info("start domain %s" % guestname)
    if root_squash == "yes":
        if virt_use_nfs == "on":
            if dynamic_ownership == "enable":
                try:
                    domobj.create()
                    logger.error("Domain %s started, this is not expected" %
                                 guestname)
                    return 1
                except libvirtError as e:
                    logger.error("API error message: %s, error code is %s"
                                 % (e.get_error_message(), e.get_error_code()))
                    logger.info("Fail to start domain %s, this is expected" %
                                guestname)

            elif dynamic_ownership == "disable":
                try:
                    domobj.create()
                    logger.error("Domain %s started, this is not expected" %
                                 guestname)
                    return 1
                except libvirtError as e:
                    logger.error("API error message: %s, error code is %s"
                                 % (e.get_error_message(), e.get_error_code()))
                    logger.info("Fail to start domain %s, this is expected" %
                                guestname)
        elif virt_use_nfs == "off":
            if dynamic_ownership == "enable":
                try:
                    domobj.create()
                    logger.error("Domain %s started, this is not expected" %
                                 guestname)
                    return 1
                except libvirtError as e:
                    logger.error("API error message: %s, error code is %s"
                                 % (e.get_error_message(), e.get_error_code()))
                    logger.info("Fail to start domain %s, this is expected" %
                                guestname)

            elif dynamic_ownership == "disable":
                try:
                    domobj.create()
                    logger.error("Domain %s started, this is not expected" %
                                 guestname)
                    return 1
                except libvirtError as e:
                    logger.error("API error message: %s, error code is %s"
                                 % (e.get_error_message(), e.get_error_code()))
                    logger.info("Fail to start domain %s, this is expected" %
                                guestname)
    elif root_squash == "no":
        if virt_use_nfs == "on":
            if dynamic_ownership == "enable":
                try:
                    domobj.create()
                    logger.info("Success start domain %s" % guestname)
                except libvirtError as e:
                    logger.error("API error message: %s, error code is %s"
                                 % (e.get_error_message(), e.get_error_code()))
                    logger.error("Fail to start domain %s" % guestname)
                    return 1

            elif dynamic_ownership == "disable":
                try:
                    domobj.create()
                    logger.error("Domain %s started, this is not expected" %
                                 guestname)
                    return 1
                except libvirtError as e:
                    logger.error("API error message: %s, error code is %s"
                                 % (e.get_error_message(), e.get_error_code()))
                    logger.info("Fail to start domain %s, this is expected" %
                                guestname)
        elif virt_use_nfs == "off":
            if dynamic_ownership == "enable":
                try:
                    domobj.create()
                    logger.error("Domain %s started, this is not expected" %
                                 guestname)
                    return 1
                except libvirtError as e:
                    logger.error("API error message: %s, error code is %s"
                                 % (e.get_error_message(), e.get_error_code()))
                    logger.info("Fail to start domain %s, this is expected" %
                                guestname)

            elif dynamic_ownership == "disable":
                try:
                    domobj.create()
                    logger.error("Domain %s started, this is not expected" %
                                 guestname)
                    return 1
                except libvirtError as e:
                    logger.error("API error message: %s, error code is %s"
                                 % (e.get_error_message(), e.get_error_code()))
                    logger.info("Fail to start domain %s, this is expected" %
                                guestname)

    logger.info("get the domain state")
    try:
        state = domobj.info()[0]
        logger.info("domain %s is %s" % (guestname, state))
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("Error: fail to get domain %s state" % guestname)
        return 1

    if state != libvirt.VIR_DOMAIN_SHUTOFF:
        logger.info("shut down the domain %s" % guestname)
        try:
            domobj.destroy()
        except libvirtError as e:
            logger.error("API error message: %s, error code is %s"
                         % (e.get_error_message(), e.get_error_code()))
            logger.error("Error: fail to destroy domain %s" % guestname)
            return 1

    logger.info("Second, start the domain after chown the img file to qemu")

    file_name = os.path.basename(disk_file)
    filepath = "/tmp/%s" % file_name
    logger.info("set chown of %s as 107:107" % filepath)
    chown_cmd = "chown 107:107 %s" % filepath
    ret, out = utils.exec_cmd(chown_cmd, shell=True)
    if ret:
        logger.error("failed to chown %s to qemu:qemu" % filepath)
        return 1

    logger.info("start domain %s" % guestname)
    if root_squash == "yes":
        if virt_use_nfs == "on":
            if dynamic_ownership == "enable":
                try:
                    domobj.create()
                    logger.info("Success start domain %s" % guestname)
                except libvirtError as e:
                    logger.error("API error message: %s, error code is %s"
                                 % (e.get_error_message(), e.get_error_code()))
                    logger.error("Fail to start domain %s" % guestname)
                    return 1

            elif dynamic_ownership == "disable":
                try:
                    domobj.create()
                    logger.info("Success start domain %s" % guestname)
                except libvirtError as e:
                    logger.error("API error message: %s, error code is %s"
                                 % (e.get_error_message(), e.get_error_code()))
                    logger.error("Fail to start domain %s" % guestname)
                    return 1

        elif virt_use_nfs == "off":
            if dynamic_ownership == "enable":
                try:
                    domobj.create()
                    logger.error("Domain %s started, this is not expected" %
                                 guestname)
                    return 1
                except libvirtError as e:
                    logger.error("API error message: %s, error code is %s"
                                 % (e.get_error_message(), e.get_error_code()))
                    logger.info("Fail to start domain %s, this is expected" %
                                guestname)

            elif dynamic_ownership == "disable":
                try:
                    domobj.create()
                    logger.error("Domain %s started, this is not expected" %
                                 guestname)
                    return 1
                except libvirtError as e:
                    logger.error("API error message: %s, error code is %s"
                                 % (e.get_error_message(), e.get_error_code()))
                    logger.info("Fail to start domain %s, this is expected" %
                                guestname)
    elif root_squash == "no":
        if virt_use_nfs == "on":
            if dynamic_ownership == "enable":
                try:
                    domobj.create()
                    logger.info("Success start domain %s" % guestname)
                except libvirtError as e:
                    logger.error("API error message: %s, error code is %s"
                                 % (e.get_error_message(), e.get_error_code()))
                    logger.error("Fail to start domain %s" % guestname)
                    return 1

            elif dynamic_ownership == "disable":
                try:
                    domobj.create()
                    logger.info("Success start Domain %s" % guestname)
                except libvirtError as e:
                    logger.error("API error message: %s, error code is %s"
                                 % (e.get_error_message(), e.get_error_code()))
                    logger.error("Fail to start domain %s" % guestname)
                    return 1

        elif virt_use_nfs == "off":
            if dynamic_ownership == "enable":
                try:
                    domobj.create()
                    logger.error("Domain %s started, this is not expected" %
                                 guestname)
                    return 1
                except libvirtError as e:
                    logger.error("API error message: %s, error code is %s"
                                 % (e.get_error_message(), e.get_error_code()))
                    logger.info("Fail to start domain %s, this is expected" %
                                guestname)

            elif dynamic_ownership == "disable":
                try:
                    domobj.create()
                    logger.error("Domain %s started, this is not expected" %
                                 guestname)
                    return 1
                except libvirtError as e:
                    logger.error("API error message: %s, error code is %s"
                                 % (e.get_error_message(), e.get_error_code()))
                    logger.info("Fail to start domain %s, this is expected" %
                                guestname)

    return 0


def domain_nfs_start_clean(params):
    """clean testing environment"""
    logger = params['logger']
    guestname = params['guestname']

    # Connect to local hypervisor connection URI
    conn = utils.get_conn()
    domobj = conn.lookupByName(guestname)

    if domobj.info()[0] != libvirt.VIR_DOMAIN_SHUTOFF:
        domobj.destroy()

    dom_xml = domobj.XMLDesc(0)
    disk_file = utils.get_disk_path(dom_xml)
    img_dir = os.path.dirname(disk_file)
    file_name = os.path.basename(disk_file)
    temp_file = "/tmp/%s" % file_name

    if os.path.ismount(img_dir):
        umount_cmd = "umount -f %s" % img_dir
        ret, out = utils.exec_cmd(umount_cmd, shell=True)
        if ret:
            logger.error("failed to umount %s" % img_dir)

    if os.path.exists(temp_file):
        os.remove(temp_file)

    clean_nfs_conf = "sed -i '$d' /etc/exports"
    utils.exec_cmd(clean_nfs_conf, shell=True)

    clean_qemu_conf = "sed -i '$d' %s" % QEMU_CONF
    utils.exec_cmd(clean_qemu_conf, shell=True)

    cmd = "service libvirtd restart"
    utils.exec_cmd(cmd, shell=True)

    return 0
