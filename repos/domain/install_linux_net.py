#! /usr/bin/env python
# Install a linux domain from network

import re
import time

from src import sharedmod
from libvirt import libvirtError
from repos.domain import install_common

required_params = ('guestname', 'guestos', 'guestarch',)
optional_params = {'memory': 1048576,
                   'vcpu': 1,
                   'disksize': 10,
                   'diskpath': '/var/lib/libvirt/images/libvirt-test-api',
                   'imageformat': 'qcow2',
                   'hddriver': 'virtio',
                   'nicdriver': 'virtio',
                   'macaddr': '52:54:00:97:e4:28',
                   'uuid': '05867c1a-afeb-300e-e55e-2673391ae080',
                   'type': 'define',
                   'xml': 'xmls/kvm_linux_guest_install_net.xml',
                   'graphic': "spice",
                   'video': 'qxl',
                   'guestmachine': 'pc',
                   'rhelnewest': '',
                   }


def install_linux_net(params):
    """install a new virtual machine by http method"""
    # Initiate and check parameters
    logger = params['logger']
    guestname = params.get('guestname')
    guestos = params.get('guestos')
    guestarch = params.get('guestarch')
    xmlstr = params['xml']
    nicdriver = params.get('nicdriver', 'virtio')
    seeksize = params.get('disksize', 10)
    hddriver = params.get('hddriver', 'virtio')
    diskpath = params.get('diskpath', '/var/lib/libvirt/images/libvirt-test-api')
    imageformat = params.get('imageformat', 'qcow2')
    graphic = params.get('graphic', 'spice')
    video = params.get('video', 'qxl')
    installtype = params.get('type', 'define')
    installmethod = params.get('installmethod', 'http')
    rhelnewest = params.get('rhelnewest')

    options = [guestname, guestos, guestarch, nicdriver, hddriver,
              imageformat, graphic, video, diskpath, seeksize, "local"]
    install_common.prepare_env(options, logger)

    install_common.remove_all(diskpath, logger)
    install_common.create_image(diskpath, seeksize, imageformat, logger)

    xmlstr = xmlstr.replace('GRAPHIC', graphic)
    xmlstr = install_common.set_disk_xml(hddriver, xmlstr, diskpath, logger)
    xmlstr = install_common.set_video_xml(video, xmlstr)
    ostree = install_common.get_ostree(rhelnewest, guestos, guestarch, logger)
    kscfg = install_common.get_kscfg(rhelnewest, guestos, guestarch, "http", logger)
    xmlstr = xmlstr.replace('KS', kscfg)

    logger.info("installation method: %s" % installmethod)
    logger.info('prepare installation...')
    xmlstr = install_common.get_vmlinuz_initrd(ostree, xmlstr, logger)
    logger.info('dump installation guest xml:\n%s' % xmlstr)

    conn = sharedmod.libvirtobj['conn']
    if not install_common.start_guest(conn, installtype, xmlstr, logger):
        logger.error("fail to define domain %s" % guestname)
        return 1

    if not install_common.wait_install(conn, guestname, xmlstr, installtype, "http", logger):
        return 1

    if not install_common.check_guest_ip(guestname, logger):
        return 1

    time.sleep(60)

    return 0


def install_linux_net_clean(params):
    """ clean testing environment """
    logger = params['logger']
    guestname = params.get('guestname')
    diskpath = params.get('diskpath', '/var/lib/libvirt/images/libvirt-test-api')

    install_common.clean_guest(guestname, logger)
    install_common.remove_all(diskpath, logger)
    install_common.remove_vmlinuz_initrd(logger)
