#! /usr/bin/env python
# Install a linux domain from network

import os
import sys
import re
import time
import commands
import shutil
import urllib


import libvirt
from libvirt import libvirtError

from src import sharedmod
from src import env_parser
from utils import utils
from repos.domain import install_common

required_params = ('guestname', 'guestos', 'guestarch', 'netmethod')
optional_params = {'memory': 1048576,
                   'vcpu': 2,
                   'disksize': 10,
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
    ret, out = commands.getstatusoutput(cmd)
    logger.info("get interface: %s" % out)
    if ret == 1:
        logger.error("fail to get interface.")
        return 1

    interface = out.split('\n')
    return interface[0]


def get_remote_hypervisor_uri(hostip, user, password):
    (ret1, out1) = utils.remote_exec_pexpect(hostip, user, password, 'lsmod|grep kvm')
    (ret2, out2) = utils.remote_exec_pexpect(hostip, user, password, 'ls /proc|grep xen')
    if strip(out1) != "":
        return "qemu+ssh://%s/system" % hostip
    elif strip == "xen":
        return "xen+ssh://%s" % hostip
    else:
        return "No hypervisor running"


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
        if "pek2" in location:
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
    seeksize = params.get('disksize', 10)

    options = [guestname, guestos, guestarch, nicdriver, hddriver,
              imageformat, graphic, video, diskpath, seeksize, "local"]
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
    logger.info("rhel newest: %s" % rhelnewest)

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

    if not install_common.check_guest_ip(guestname, logger):
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
