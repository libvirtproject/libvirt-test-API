#!/usr/bin/env python
# Attach a disk device to domain

import time

from libvirt import libvirtError
from src import sharedmod
from utils import utils, process

required_params = ('guestname', 'hddriver')
optional_params = {'imagesize': 1,
                   'imageformat': 'raw',
                   'qcow2version': 'basic',
                   'username': 'root',
                   'password': 'redhat',
                   'volumepath': '/var/lib/libvirt/images',
                   'volume': 'attacheddisk',
                   'xml': 'xmls/disk.xml',
                   }


def create_image(disk, xmlstr, seeksize, imageformat, qcow2version):
    """Create a image file"""

    if imageformat == 'raw':
        qcow2_options = ""
    elif qcow2version.startswith('v3'):
        qcow2_options = "-o compat=1.1"
        if qcow2version.endswith('lazy_refcounts'):
            qcow2_options = qcow2_options + " -o lazy_refcounts=on"
    cmd = ("qemu-img create -f %s %s %s %sG" %
           (imageformat, qcow2_options, disk, seeksize))
    logger.debug("cmd: %s" % cmd)
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status != 0:
        logger.debug(ret.stdout)
        return 1

    if "readonly" in xmlstr:
        cmd = "mkfs.ext3 -F " + disk
        logger.debug("cmd: %s" % cmd)
        ret = process.run(cmd, shell=True, ignore_status=True)
        if ret.exit_status != 0:
            logger.debug(ret.stdout)
            return 1
    return 0


def check_attach_disk(num1, num2):
    """Check attach disk result via simple disk number comparison """
    if num2 > num1:
        return True
    else:
        return False


def check_disk_permission(guestname, devname, username, password):
    """Check the permission of attached disk in guest"""
    mac = utils.get_dom_mac_addr(guestname)
    logger.debug("the mac address of vm %s is %s" % (guestname, mac))
    ip = utils.mac_to_ip(mac, 300)
    logger.debug("the ip address of vm %s is %s" % (guestname, ip))

    cmd = "mount /dev/" + devname + " /mnt"
    (ret, output) = utils.remote_exec_pexpect(ip, username, password, cmd)
    if not ret:
        logger.info("Login guest to run mount /dev/%s /mnt : %s" % (devname,
                                                                    output))
        if "write-protected" in output and "read-only" in output:
            touchcmd = "touch test /mnt"
            (ret, output) = utils.remote_exec_pexpect(ip, username, password,
                                                      touchcmd)
            if ret:
                logger.info("Login guest to touch test /mnt : %s" % output)
                if "Read-only file system" in output:
                    (ret, output) = utils.remote_exec_pexpect(ip, username,
                                                              password, "umount /mnt")
                    return True
            else:
                logger.error("Fail: touch file failed.")
                return False
        else:
            logger.error("Fail: %s don't write-protected." % devname)
            return False
    else:
        logger.error("Failed to mount /dev/%s" % devname)
        logger.error("ret = %s, out = %s" % (ret, output))
        return False


def attach_disk(params):
    """ Attach a disk to domain from xml """
    global logger
    logger = params['logger']
    guestname = params['guestname']
    hddriver = params['hddriver']
    xmlstr = params['xml']
    imagesize = int(params.get('imagesize', 1))
    imageformat = params.get('imageformat', 'raw')
    qcow2version = params.get('qcow2version', 'v3')
    volumepath = params.get('volumepath', '/var/lib/libvirt/images')
    volume = params.get('volume', 'attacheddisk')

    disk = volumepath + "/" + volume
    xmlstr = xmlstr.replace('DISKPATH', disk)

    conn = sharedmod.libvirtobj['conn']
    # Create image, qcow2version includes 'v3', 'v3_lazy_refcounts'
    if create_image(disk, xmlstr, imagesize, imageformat, qcow2version):
        logger.error("fail to create a image file")
        return 1

    domobj = conn.lookupByName(guestname)

    if hddriver == 'virtio':
        xmlstr = xmlstr.replace('DEV', 'vdb')
        devname = "vdb"
    elif hddriver == 'ide':
        xmlstr = xmlstr.replace('DEV', 'hdb')
        devname = "hdb"
    elif hddriver == 'scsi':
        xmlstr = xmlstr.replace('DEV', 'sdb')
        devname = "sdb"
    logger.info("disk xml:\n%s" % xmlstr)

    disk_num1 = utils.dev_num(guestname, "disk")
    logger.debug("original disk number: %s" % disk_num1)

    try:
        #Attach disk to domain
        domobj.attachDevice(xmlstr)
        time.sleep(90)
        disk_num2 = utils.dev_num(guestname, "disk")
        logger.debug("update disk number to %s" % disk_num2)

        if check_attach_disk(disk_num1, disk_num2):
            logger.info("current disk number: %s\n" % disk_num2)
        else:
            logger.error("fail to attach a disk to guest: %s\n" % disk_num2)
            return 1

        if "readonly" in xmlstr:
            # Check the disk in guest
            username = params.get('username', 'root')
            password = params.get('password', 'redhat')
            if check_disk_permission(guestname, devname, username, password):
                return 0
            else:
                return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("attach %s disk to guest %s" % (volumepath, guestname))
        return 1

    return 0
