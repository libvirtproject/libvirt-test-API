#! /usr/bin/env python
# Install a linux domain from network

import os
import time

from src import sharedmod
from utils import utils, process
from repos.installation import install_common

required_params = ('guestname', 'guestos', 'guestarch', 'netmethod')
optional_params = {'memory': 4194304,
                   'vcpu': 2,
                   'disksize': 14,
                   'imageformat': 'qcow2',
                   'hddriver': 'virtio',
                   'nicdriver': 'virtio',
                   'nettype': 'network',
                   'netsource': 'default',
                   'type': 'define',
                   'xml': 'xmls/kvm_linux_guest_install_net.xml',
                   'guestmachine': 'pc',
                   'graphic': 'spice',
                   'video': 'qxl',
                   'hostip': '127.0.0.1',
                   'user': 'root',
                   'password': 'redhat',
                   'disksymbol': 'sdb',
                   'diskpath': "/var/lib/libvirt/images/libvirt-test-api",
                   'rhelnewest': '',
                   }

BOOT_DIR = "/var/lib/libvirt/boot"
VMLINUZ = os.path.join(BOOT_DIR, 'vmlinuz')
INITRD = os.path.join(BOOT_DIR, 'initrd.img')


def get_interface(logger):
    # ip addr show | grep 'state UP' | awk '{print $2}' | cut -d':' -f1
    cmd = ("ip addr show | grep \'state UP\' | awk \'{print $2}\'"
           "| cut -d\':\' -f1")
    logger.info(cmd)
    ret = process.run(cmd, shell=True, ignore_status=True)
    logger.info("get interface: %s" % ret.stdout)
    if ret.exit_status == 1:
        logger.error("fail to get interface. %s" % ret.stdout)
        return 1

    interface = ret.stdout.split('\n')
    return interface[0]


def set_xml(rhelnewest, xmlstr, installmethod, guestos, guestarch, logger):
    location = utils.get_local_hostname()
    if installmethod == 'http':
        ks = install_common.get_kscfg(rhelnewest, guestos, guestarch, "http", logger)
        ostree = install_common.get_ostree(rhelnewest, guestos, guestarch, logger)
        nettype = "network"
        netsource = "default"
    elif installmethod == 'ftp':
        ks = install_common.get_kscfg(rhelnewest, guestos, guestarch, "ftp", logger)
        ostree = install_common.get_ostree(rhelnewest, guestos, guestarch, logger)
        nettype = "network"
        netsource = "default"
    elif installmethod == "nfs":
        ostree = install_common.get_ostree(rhelnewest, guestos, guestarch, logger)
        if "pek2" in location or "nay" in location:
            ks = install_common.get_kscfg(rhelnewest, guestos, guestarch, "local_nfs", logger)
        else:
            ks = install_common.get_kscfg(rhelnewest, guestos, guestarch, "remote_nfs", logger)
        nettype = "bridge"
        netsource = "br0"
        interface = get_interface(logger)
        xmlstr = xmlstr.replace('INTERFACE', interface)

    xmlstr = xmlstr.replace('KS', ks)

    logger.debug('install source:\n    %s' % ostree)
    logger.debug('kisckstart file:\n    %s' % ks)

    logger.info('prepare installation...')
    xmlstr = install_common.get_vmlinuz_initrd(ostree, xmlstr, logger)
    xmlstr = xmlstr.replace('NETTYPE', nettype)
    xmlstr = xmlstr.replace('NETSOURCE', netsource)
    return xmlstr


def install_linux_net_remote(params):
    """install a new virtual machine"""
    # Initiate and check parameters
    logger = params['logger']

    guestname = params.get('guestname')
    guestos = params.get('guestos')
    guestarch = params.get('guestarch')
    nettype = params.get('nettype')
    netsource = params.get('netsource')
    xmlstr = params['xml']
    installmethod = params['netmethod']
    hostip = params.get('hostip', '127.0.0.1')
    user = params.get('user', 'root')
    password = params.get('password', 'redhat')
    graphic = params.get('graphic', 'spice')
    video = params.get('video', 'qxl')
    hddriver = params.get('hddriver', 'virtio')
    nicdriver = params.get('nicdriver', 'virtio')
    diskpath = params.get('diskpath', "/var/lib/libvirt/images/libvirt-test-api")
    installtype = params.get('type', 'define')
    rhelnewest = params.get("rhelnewest")
    imageformat = params.get('imageformat', 'qcow2')
    seeksize = params.get('disksize', 14)

    options = [guestname, guestos, guestarch, nicdriver, hddriver, imageformat, graphic, video, diskpath, seeksize, "local"]
    install_common.prepare_env(options, logger)

    install_common.remove_all(diskpath, logger)
    install_common.create_image(diskpath, seeksize, imageformat, logger)

    logger.info("rhelnewest: %s" % rhelnewest)
    xmlstr = xmlstr.replace('GRAPHIC', graphic)
    xmlstr = install_common.set_disk_xml(hddriver, xmlstr, diskpath, logger)
    xmlstr = install_common.set_video_xml(video, xmlstr)

    macaddr = utils.get_rand_mac()

    logger.info("the installation method is %s" % installmethod)
    logger.info("the macaddress is %s" % macaddr)

    xmlstr = set_xml(rhelnewest, xmlstr, installmethod, guestos, guestarch, logger)

    logger.debug("vmlinuz and initrd.img are located in %s" % BOOT_DIR)

    xmlstr = xmlstr.replace('MACADDR', macaddr)
    xmlstr = xmlstr.replace('DISKPATH', diskpath)

    logger.debug('dump installation guest xml:\n%s' % xmlstr)

    conn = sharedmod.libvirtobj['conn']
    if not install_common.start_guest(conn, installtype, xmlstr, logger):
        logger.error("fail to define domain %s" % guestname)
        return 1

    if not install_common.wait_install(conn, guestname, xmlstr, installtype, installmethod, logger):
        return 1

    time.sleep(60)
    return 0


def install_linux_net_remote_clean(params):
    """ clean testing environment """
    logger = params['logger']
    guestname = params.get('guestname')
    diskpath = params.get('diskpath', "/var/lib/libvirt/images/libvirt-test-api")

    install_common.clean_guest(guestname, logger)
    install_common.remove_all(diskpath, logger)
    install_common.remove_all(VMLINUZ, logger)
    install_common.remove_all(INITRD, logger)
