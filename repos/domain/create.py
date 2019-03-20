#!/usr/bin/env python
# Create domain from xml

import os
import time
import shutil
import libvirt

from libvirt import libvirtError

from src import sharedmod
from utils import utils

NONE = 0
START_PAUSED = 1

required_params = ('guestname',)
optional_params = {'memory': 2097152,
                   'vcpu': 1,
                   'imagepath': '/var/lib/libvirt/images/libvirt-ci.qcow2',
                   'diskpath': '/var/lib/libvirt/images/libvirt-test-api',
                   'imageformat': 'qcow2',
                   'hddriver': 'virtio',
                   'nicdriver': 'virtio',
                   'macaddr': '52:54:00:97:e4:28',
                   'uuid': '05867c1a-afeb-300e-e55e-2673391ae080',
                   'virt_type': 'kvm',
                   'flags': 'none',
                   'xml': 'xmls/kvm_guest_define.xml',
                   'guestarch': 'x86_64',
                   'guestmachine': 'pc',
                   'on_poweroff': 'destroy',
                   'on_reboot': 'restart',
                   'on_crash': 'restart',
                   'video': 'qxl',
                   'graphic': 'spice'
                   }


def create(params):
    """create a domain from xml"""
    logger = params['logger']
    guestname = params['guestname']
    xmlstr = params['xml']

    flags = params.get('flags', 'none')
    if flags != "none" and flags != "start_paused":
        logger.error("flags value either \"none\" or \"start_paused\"")
        return 1

    uuid = params.get('uuid', '05867c1a-afeb-300e-e55e-2673391ae080')
    xmlstr = xmlstr.replace('UUID', uuid)

    guestarch = params.get('guestarch', 'x86_64')
    guestmachine = params.get('guestmachine', 'pc')
    video = params.get('video', 'qxl')
    graphic = params.get('graphic', 'spice')

    xmlstr = xmlstr.replace('GUESTARCH', guestarch)
    xmlstr = xmlstr.replace('GUESTMACHINE', guestmachine)
    xmlstr = xmlstr.replace('VIDEO', video)
    xmlstr = xmlstr.replace('GRAPHIC', graphic)

    imagepath = params.get('imagepath', '/var/lib/libvirt/images/libvirt-ci.qcow2')
    logger.info("using image %s" % imagepath)
    diskpath = params.get('diskpath', '/var/lib/libvirt/images/libvirt-test-api')
    logger.info("disk image is %s" % diskpath)

    shutil.copyfile(imagepath, diskpath)
    os.chown(diskpath, 107, 107)

    conn = sharedmod.libvirtobj['conn']

    # Create domain from xml
    try:
        if flags == "none":
            domobj = conn.createXML(xmlstr, NONE)
        elif flags == "start_paused":
            domobj = conn.createXML(xmlstr, START_PAUSED)
        else:
            logger.error("flags error")
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("fail to create domain %s" % guestname)
        return 1

    if flags == "start_paused":
        state = domobj.info()[0]
        if state == libvirt.VIR_DOMAIN_PAUSED:
            logger.info("guest start with state paused successfully")
            return 0
        else:
            logger.error("guest state error")
            return 1

    logger.info("get the mac address of vm %s" % guestname)
    mac = utils.get_dom_mac_addr(guestname)
    logger.info("the mac address of vm %s is %s" % (guestname, mac))

    timeout = 600

    while timeout:
        time.sleep(10)
        timeout -= 10

        ip = utils.mac_to_ip(mac, 180)

        if not ip:
            logger.info(str(timeout) + "s left")
        else:
            logger.info("vm %s power on successfully" % guestname)
            logger.info("the ip address of vm %s is %s" % (guestname, ip))
            break

        if timeout == 0:
            logger.info("fail to power on vm %s" % guestname)
            return 1

    return 0
