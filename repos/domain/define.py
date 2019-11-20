#!/usr/bin/evn python

import os
import re
import sys
import string
import pexpect
import shutil

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils
from repos.domain import domain_common

required_params = ('guestname',)
optional_params = {'memory': 1048576,
                   'vcpu': 1,
                   'transport': '',
                   'auth_tcp': '',
                   'imagepath': '/var/lib/libvirt/images/libvirt-ci.qcow2',
                   'diskpath': '/var/lib/libvirt/images/libvirt-test-api',
                   'imageformat': 'qcow2',
                   'hddriver': 'virtio',
                   'nicdriver': 'virtio',
                   'macaddr': '52:54:00:97:e4:28',
                   'uuid': '05867c1a-afeb-300e-e55e-2673391ae080',
                   'target_machine': None,
                   'username': None,
                   'password': None,
                   'virt_type': 'kvm',
                   'xml': 'xmls/kvm_guest_define.xml',
                   'guestarch': 'x86_64',
                   'guestmachine': 'pc',
                   'networksource': 'default',
                   'bootdev': 'hd',
                   'vncpasswd': '',
                   'on_poweroff': 'destroy',
                   'on_reboot': 'restart',
                   'on_crash': 'restart',
                   }


def check_define_domain(guestname, virt_type, ip, username,
                        password, logger):
    """Check define domain result, if define domain is successful,
       guestname.xml will exist under /etc/libvirt/qemu/
       and can use virt-xml-validate tool to check the file validity
    """
    if "kvm" in virt_type:
        path = "/etc/libvirt/qemu/%s.xml" % guestname
    elif "xen" in virt_type:
        path = "/etc/xen/%s" % guestname
    elif "lxc" in virt_type:
        path = "/etc/libvirt/lxc/%s.xml" % guestname
    else:
        logger.error("unknown virt type")

    if ip:
        cmd = "ls %s" % path
        ret, output = utils.remote_exec_pexpect(ip, username,
                                                password, cmd)
        if ret:
            logger.error("guest %s xml file doesn't exsits" % guestname)
            return False
        else:
            return True
    else:
        if os.access(path, os.R_OK):
            return True
        else:
            return False


def define(params):
    """Define a domain from xml"""
    logger = params['logger']
    guestname = params['guestname']

    xmlstr = params['xml']
    if utils.isPower():
        guestarch = "ppc64le"
        guestmachine = "persies"
        xmlstr = xmlstr.replace('GUESTARCH', guestarch)
        xmlstr = xmlstr.replace('GUESTMACHINE', guestmachine)

    logger.debug("domain xml:\n%s" % xmlstr)

    imagepath = params.get('imagepath', '/var/lib/libvirt/images/libvirt-ci.qcow2')
    logger.info("using image %s" % imagepath)
    diskpath = params.get('diskpath', '/var/lib/libvirt/images/libvirt-test-api')
    logger.info("disk image is %s" % diskpath)

    shutil.copyfile(imagepath, diskpath)
    os.chown(diskpath, 107, 107)

    transport = params.get('transport', '')
    auth_tcp = params.get('auth_tcp', '')
    target_machine = params.get('target_machine', '')
    username = params.get('username', '')
    password = params.get('password', '')
    virt_type = params.get('virt_type', 'kvm')
    uuid = params.get('uuid', '05867c1a-afeb-300e-e55e-2673391ae080')
    xmlstr = xmlstr.replace('UUID', uuid)

    if target_machine == '':
        if "lxc" in virt_type:
            conn = libvirt.open("lxc:///")
        else:
            conn = sharedmod.libvirtobj['conn']

        uri = conn.getURI()
    else:
        #generate ssh key pair
        ret = domain_common.ssh_keygen(logger)
        if ret:
            logger.error("failed to generate RSA key")
            return 1

        #setup ssh tunnel with target machine
        ret = domain_common.ssh_tunnel(target_machine, username, password, logger)
        if ret:
            logger.error("faild to setup ssh tunnel with target machine %s" % target_machine)
            return 1

        if transport == 'ssh':
            uri = 'qemu+ssh://root@%s/system' % target_machine
        elif transport == 'tls':
            uri = 'qemu://%s/system' % target_machine
        elif transport == 'tcp':
            uri = 'qemu+tcp://%s/system' % target_machine
        else:
            uri = 'qemu:///system'

        if auth_tcp == '':
            conn = libvirt.open(uri)
        elif auth_tcp == 'sasl':
            user_data = [username, password]
            auth = [[libvirt.VIR_CRED_AUTHNAME, libvirt.VIR_CRED_PASSPHRASE],
                    domain_common.request_credentials, user_data]
            conn = libvirt.openAuth(uri, auth, 0)

    logger.info("define domain on %s" % uri)

    imageformat = params.get('imageformat', 'qcow2')
    xmlstr = xmlstr.replace('IMAGEFORMAT', imageformat)

    hddriver = params.get('hddriver', 'virtio')
    if hddriver == 'virtio':
        xmlstr = xmlstr.replace('DEV', 'vda')
    elif hddriver == 'ide':
        xmlstr = xmlstr.replace('DEV', 'hda')
    elif hddriver == 'scsi':
        xmlstr = xmlstr.replace('DEV', 'sda')

    bootdev = params.get('bootdev', 'hd')

    # Define domain from xml
    try:
        conn.defineXML(xmlstr)
        if check_define_domain(guestname, virt_type, target_machine,
                               username, password, logger):
            logger.info("define a domain form xml is successful")
        else:
            logger.error("fail to check define domain")
            return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    return 0
