#!/usr/bin/evn python

import os
import re
import sys
import commands
import string
import pexpect

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('guestname', 'diskpath',)
optional_params = {'memory': 1048576,
                   'vcpu': 1,
                   'imageformat': 'qcow2',
                   'hddriver': 'virtio',
                   'nicdriver': 'virtio',
                   'macaddr': '52:54:00:97:e4:28',
                   'uuid': '05867c1a-afeb-300e-e55e-2673391ae080',
                   'username': None,
                   'password': None,
                   'virt_type': 'kvm',
                   'xml': 'xmls/kvm_guest_define.xml',
                   'guestarch': 'x86_64',
                   'guestmachine': 'pc',
                   'networksource': 'default',
                   'bootdev': 'hd',
                   }


def check_define_domain(guestname, virt_type, hostname, username,
                        password, logger):
    """Check define domain result, if define domain is successful,
       guestname.xml will exist under /etc/libvirt/qemu/
       and can use virt-xml-validate tool to check the file validity
    """
    if "kvm" in virt_type:
        path = "/etc/libvirt/qemu/%s.xml" % guestname
    elif "xen" in virt_type:
        path = "/etc/xen/%s" % guestname
    else:
        logger.error("unknown virt type")

    if hostname:
        cmd = "ls %s" % path
        ret, output = utils.remote_exec_pexpect(hostname, username,
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
    logger.debug("domain xml:\n%s" % xmlstr)

    conn = sharedmod.libvirtobj['conn']
    uri = conn.getURI()

    hostname = utils.parse_uri(uri)[1]
    username = params.get('username', '')
    password = params.get('password', '')
    virt_type = params.get('virt_type', 'kvm')

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
        if check_define_domain(guestname, virt_type, hostname,
                               username, password, logger):
            logger.info("define a domain form xml is successful")
        else:
            logger.error("fail to check define domain")
            return 1
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
