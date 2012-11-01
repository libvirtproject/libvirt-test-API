#!/usr/bin/env python
# cdrom & floppy update testing

import os
import re
import sys
import time
from xml.dom import minidom

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('guestname', 'username', 'password', 'diskpath', 'devtype',)
optional_params = {'memory': 1048576,
                   'vcpu': 1,
                   'imageformat' : 'raw',
                   'hddriver' : 'virtio',
                   'nicdriver': 'virtio',
                   'macaddr': '52:54:00:97:e4:28',
                   'uuid' : '05867c1a-afeb-300e-e55e-2673391ae080',
                   'virt_type': 'kvm',
                   'xml': 'xmls/kvm_guest_define_with_cdrom_and_floppy.xml',
                   'cdrom_xml': 'xmls/cdrom.xml',
                   'floppy_xml': 'xmls/floppy.xml',
                   'guestarch': 'x86_64',
                   'guestmachine': 'pc',
                   'isopath': '/tmp/cdrom.iso',
                   'floppypath': '/tmp/floppy.img',
                  }

def create_image(devtype, img_name, logger):
    """Create an image file"""
    if devtype == 'cdrom':
        cmd1 = "uuidgen|cut -d- -f1"
        ret1, out1 = utils.exec_cmd(cmd1, shell=True)
        if ret1:
            logger.error("random code generated fail.")
            return False

        cmd2 = "mkdir /tmp/%s && touch /tmp/%s/$(uuidgen|cut -d- -f1)" \
                                                   % (out1, out1)
        ret2, out2 = utils.exec_cmd(cmd2, shell=True)
        if ret2:
            logger.error("fail to create files for iso image: \n %s" % out1)
            return False
        else:
            logger.info("prepare files for iso image creation")

        cmd3 = "genisoimage -o %s /tmp/%s" % (img_name, out1)
        ret3, out3 = utils.exec_cmd(cmd3, shell=True)
        if ret3:
            logger.error("iso file creation fail: \n %s" % out1)
            return False
        else:
            logger.info("create an image: %s" % img_name)

    elif devtype == 'floppy':
        cmd1 = "dd if=/dev/zero of=%s bs=1440k count=1" % img_name
        ret1, out1 = utils.exec_cmd(cmd1, shell=True)
        if ret1:
            logger.error("floppy image creation fail: \n %s" % out1)
            return False
        else:
            logger.info("create an image for floppy use: %s" % img_name)

        cmd2 = "mkfs.msdos -s 1 %s" % img_name
        ret2, out2 = utils.exec_cmd(cmd2, shell=True)
        if ret2:
            logger.error("fail to format image: \n %s" % out2)
            return False
        else:
            logger.info("succeed to format image: %s" % img_name)

        cmd3 = "mount -o loop %s /mnt && touch /mnt/$(uuidgen|cut -d- -f1) \
                                      && umount -l /mnt" % img_name
        ret3, out3 = utils.exec_cmd(cmd3, shell=True)
        if ret3:
            logger.error("fail to write file to floppy image: \n %s" % out3)
            return False
        else:
            logger.info("succeed to write file to floopy image: %s" % img_name)

    else:
        logger.error("wrong device type was specified.")
        return False

    return True

def check_device_in_guest(devtype, guestip, username, password, logger):
    """Check updated device in guest"""
    if devtype == 'cdrom':
        cmd = "mount -o loop /dev/cdrom /media"
    elif devtype == 'floppy':
        cmd = "mount /dev/fd0 /media"
    else:
        logger.error("it's not a cdrom or floppy device.")
        return False, None

    ret, output = utils.remote_exec_pexpect(guestip, username, password, cmd)
    logger.debug(output)
    if ret:
        logger.error("failed to mount %s device." % devtype)
        return False, output

    time.sleep(5)

    cmd = "ls /media"
    ret, output = utils.remote_exec_pexpect(guestip, username, password, cmd)
    logger.debug(output)
    if ret:
        logger.error("failed to list contents of %s device" % devtype)
        return False, output

    time.sleep(5)

    ret = utils.remote_exec_pexpect(guestip, username, password, "umount /media")
    if ret[0]:
        logger.error("failed to unmount %s device." % params['devtype'])
        return False, ret[1]

    return True, output

def check_updated_xml(domobj, devtype, srcfile, logger):
    """Check if the device is updated"""
    xmlobj = domobj.XMLDesc(0)
    domxml = minidom.parseString(xmlobj)
    upfile = ''

    if devtype == 'cdrom':
        for diskTag in domxml.getElementsByTagName("source"):
            if diskTag.parentNode.getAttribute("device") == 'cdrom':
                upfile = diskTag.getAttribute("file")
    elif devtype == 'floppy':
        for diskTag in domxml.getElementsByTagName("source"):
            if diskTag.parentNode.getAttribute('device') == 'floppy':
                upfile = diskTag.getAttribute("file")

    if upfile == srcfile:
        logger.debug("The %s in domain xml is updated" % devtype)
        return 0
    else:
        logger.error("The %s in domain xml is not updated" % devtype)
        return 1

def update_devflag(params):
    """Update virtual device to a domain from xml"""

    logger = params['logger']
    guestname = params['guestname']
    devtype = params['devtype']
    username = params['username']
    password = params['password']
    xmlstr = params['xml']

    cdrom_xml = params.get('cdrom_xml', 'xmls/cdrom.xml')
    floppy_xml = params.get('floppy_xml', 'xmls/floppy.xml')
    iso_path = params.get('isopath', '/tmp/cdrom.iso')
    floppy_path = params.get('floppy_path', '/tmp/floppy.img')

    pwd = os.getcwd()
    result = re.search('(.*)libvirt-test-API', pwd)
    homepath = result.group(0)

    conn = sharedmod.libvirtobj['conn']

    logger.debug("domain xml:\n%s" % xmlstr)
    logger.info("define domain with empty cdrom and floppy")
    try:
        domobj = conn.defineXML(xmlstr)
        domobj.create()
    except libvirtError, e:
        logger.info("libvirt call failed: " + str(e))
        return 1

    logger.info("waiting domain to boot up")
    time.sleep(60)
    mac = utils.get_dom_mac_addr(guestname)
    guestip = utils.mac_to_ip(mac, 180)
    logger.debug("ip address: %s" % guestip)

    if devtype == 'cdrom':
        srcpath = iso_path
        devxml = cdrom_xml
        change = 'ISOPATH'
    elif devtype == 'floppy':
        devxml = floppy_xml
        srcpath = floppy_path
        change = 'FLOPPYPATH'
    else:
        logger.error("devtype %s is not cdrom or floppy" % devtype)
        return 1

    xmlpath = homepath + '/repos/domain/' + devxml
    f = open(xmlpath, 'r')
    devxml = f.read()
    devxmlstr = devxml.replace(change, srcpath)

    if not create_image(devtype, srcpath, logger):
        logger.error("fail to create new image.")
        return 1

    logger.debug("block device xml desc for update:\n%s" % devxmlstr)

    flags = libvirt.VIR_DOMAIN_DEVICE_MODIFY_LIVE
    logger.info("insert disk into domain's %s with live flag: %s" %
                (devtype, flags))
    try:
        domobj.updateDeviceFlags(devxmlstr, flags)
        logger.debug("domain xml after updating:\n%s" % domobj.XMLDesc(0))
    except libvirtError, e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    if check_updated_xml(domobj, devtype, srcpath, logger):
        return 1

    ret = check_device_in_guest(devtype, guestip, username, password, logger)
    if not ret[0]:
        logger.error("fail to update '%s' device: %s\n" % (devtype, ret[1]))
        return 1
    else:
        logger.info("success to update '%s' device: %s\n" % (devtype, ret[1]))

    logger.info("update domain's %s with new disk file: %s" % (devtype, flags))
    logger.info("prepare new %s disk file" % devtype)
    if devtype == 'cdrom':
        srcpath = '/tmp/cdrom_new.iso'
    else:
        srcpath = '/tmp/floppy_new.img'

    if not create_image(devtype, srcpath, logger):
        logger.error("fail to create new image.")
        return 1

    new_devxml = devxml.replace(change, srcpath)

    try:
        domobj.updateDeviceFlags(new_devxml, flags)
        logger.debug("domain xml after updating:\n%s" % domobj.XMLDesc(0))
    except libvirtError, e:
        logger.error("libvirt call failed: " + str(e))
        logger.info("this is expected, %s is mounted in domain" % devtype)

    if check_updated_xml(domobj, devtype, srcpath, logger):
        return 1

    ret1 = check_device_in_guest(devtype, guestip, username, password, logger)
    if not ret1[0]:
        logger.error("fail to update '%s' device: %s\n" % (devtype, ret1[1]))
        return 1
    elif ret1[1] == ret[1]:
        logger.error("fail to update '%s' device: %s\n" % (devtype, ret1[1]))
        return 1
    else:
        logger.info("success to update '%s' device: %s\n" % (devtype, ret1[1]))

    if devtype == 'cdrom':
        srcpath = ''
    else:
        srcpath = ''

    new_devxml = devxml.replace(change, srcpath)

    flags = libvirt.VIR_DOMAIN_DEVICE_MODIFY_FORCE|libvirt.VIR_DOMAIN_DEVICE_MODIFY_LIVE
    logger.info("eject %s disk in domain with flags: %s" % (devtype, flags))
    try:
        domobj.updateDeviceFlags(new_devxml, flags)
        logger.debug("domain xml after updating:\n%s" % domobj.XMLDesc(0))
    except libvirtError, e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    if check_updated_xml(domobj, devtype, srcpath, logger):
        return 1

    ret2 = check_device_in_guest(devtype, guestip, username, password, logger)
    if not ret2[0]:
        logger.error("fail to update '%s' device: %s\n" % (devtype, ret2[1]))
        return 1
    elif ret2[1] == ret1[1]:
        logger.error("fail to update '%s' device: %s\n" % (devtype, ret2[1]))
        return 1
    else:
        logger.info("success to update '%s' device: %s\n" % (devtype, ret2[1]))

    return 0

def update_devflag_clean(params):
    """Clean testing environment"""
    logger = params['logger']

    if params['devtype'] == 'cdrom':
        os.unlink('/tmp/cdrom.iso')
        os.unlink('/tmp/cdrom_new.iso')
    elif params['devtype'] == 'floppy':
        os.unlink('/tmp/floppy.img')
        os.unlink('/tmp/floppy_new.img')
    else:
        logger.debug("image file does not exist or has been already removed.")
