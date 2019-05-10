#!/usr/bin/env python

import libvirt
import lxml
import lxml.etree

from libvirt import libvirtError
from utils import utils

required_params = ('guestname',)
optional_params = {'conn': 'qemu:///system'}


def find_iothreadid_fromxml(vm, running, iothreadid):
    if (running == 1):
        tree = lxml.etree.fromstring(vm.XMLDesc(0))
    else:
        tree = lxml.etree.fromstring(
            vm.XMLDesc(libvirt.VIR_DOMAIN_XML_INACTIVE))

    set = tree.xpath("//iothreadids/iothread")
    for n in set:
        ids = n.attrib['id']
        if int(ids) == iothreadid:
            return True

    return False


def info_iothread(params):
    """
       test API for ioThreadInfo in class virDomain
    """

    logger = params['logger']
    fail = 0

    if utils.check_qemu_package("qemu-kvm") and not utils.version_compare("qemu-kvm", 2, 12, 0, logger):
        logger.info("Current qemu-kvm don't support this API.")
        return 0

    try:
        conn = libvirt.open(params['conn'])

        logger.info("get connection to libvirtd")
        guest = params['guestname']
        vm = conn.lookupByName(guest)
        logger.info("test guest name: %s" % guest)

        """ test effect guest running XML """
        if vm.isActive() == 1:
            logger.info("guest is running test with running guest")

            ret = vm.ioThreadInfo(libvirt.VIR_DOMAIN_AFFECT_LIVE)

            if len(ret) == 0:
                vm.addIOThread(1, libvirt.VIR_DOMAIN_AFFECT_LIVE)
                if not find_iothreadid_fromxml(vm, 1, 1):
                    logger.info("FAIL: cannot find iothread id in XML")
                    return 1
                else:
                    ret = vm.ioThreadInfo(libvirt.VIR_DOMAIN_AFFECT_LIVE)

            for n in ret:
                if not find_iothreadid_fromxml(vm, 1, n[0]):
                    logger.info("FAIL: cannot find iothread id in XML")
                    fail = 1

        """ test effect guest config"""
        logger.info("test with guest inactive XML")
        ret = vm.ioThreadInfo(libvirt.VIR_DOMAIN_AFFECT_CONFIG)

        if len(ret) == 0:
            vm.addIOThread(1, libvirt.VIR_DOMAIN_AFFECT_CONFIG)
            if not find_iothreadid_fromxml(vm, 0, 1):
                logger.info("FAIL: cannot find iothread id in XML")
                return 1
            else:
                ret = vm.ioThreadInfo(libvirt.VIR_DOMAIN_AFFECT_CONFIG)

        for n in ret:
            if not find_iothreadid_fromxml(vm, 0, n[0]):
                logger.info("FAIL: cannot find iothread id in XML")
                fail = 1

    except libvirtError as e:
        logger.error("API error message: %s" % e.get_error_message())
        fail = 1
    return fail
