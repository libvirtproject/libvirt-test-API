#!/usr/bin/env python
# Attach a disk device to domain

import commands

from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('guestname', 'hddriver')
optional_params = {'imagesize': 1,
                   'imageformat': 'raw',
                   'username': 'root',
                   'password': 'redhat',
                   'volumepath' : '/var/lib/libvirt/images',
                   'volume' : 'attacheddisk',
                   'xml' : 'xmls/disk.xml',
                  }

def create_image(disk, xmlstr, seeksize, imageformat):
    """Create a image file"""

    disk_create = "qemu-img create -f %s %s %sG" % \
                    (imageformat, disk, seeksize)
    logger.debug("the command line of creating disk images is '%s'" % \
                   disk_create)
    (status, message) = commands.getstatusoutput(disk_create)
    if status != 0:
        logger.debug(message)
        return 1

    if "readonly" in xmlstr:
        make_fs = "mkfs.ext3 -F " + disk
        logger.debug("the command line of make file system is '%s'" % make_fs)
        (status, message) = commands.getstatusoutput(make_fs)
        if status != 0:
            logger.debug(message)
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
        logger.info("Login guest to run mount /dev/%s /mnt : %s" % (devname, \
                                                                    output))
        if "is write-protected, mounting read-only" in output:
            touchcmd = "touch test /mnt"
            (ret, output) = utils.remote_exec_pexpect(ip, username, password,\
                                                      touchcmd)
            if not ret:
                logger.info("Login guest to touch test /mnt : %s" % output)
                if "Read-only file system" in output:
                    (ret, output) = utils.remote_exec_pexpect(ip, username, \
                                                    password, "umount /mnt")
                    return True
    else:
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
    volumepath = params.get('volumepath', '/var/lib/libvirt/images')
    volume = params.get('volume', 'attacheddisk')

    disk = volumepath + "/" + volume
    print disk
    xmlstr = xmlstr.replace('DISKPATH', disk)

    conn = sharedmod.libvirtobj['conn']
    # Create image
    if create_image(disk, xmlstr, imagesize, imageformat):
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
        disk_num2 = utils.dev_num(guestname, "disk")
        logger.debug("update disk number to %s" %disk_num2)

        if  check_attach_disk(disk_num1, disk_num2):
            logger.info("current disk number: %s\n" %disk_num2)
        else:
            logger.error("fail to attach a disk to guest: %s\n" % disk_num2)
            return 1

        if "readonly" in xmlstr:
        # Check the disk in guest
            username = params.get('username', 'root')
            print username
            password = params.get('password', 'redhat')
            print password
            if check_disk_permission(guestname, devname, username, password):
                return 0
            else:
                return 1
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s" \
                     % (e.message, e.get_error_code()))
        logger.error("attach %s disk to guest %s" % (volumepath, guestname))
        return 1

    return 0
