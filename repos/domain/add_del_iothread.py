#!/usr/bin/env python

import libvirt
from libvirt import libvirtError
import lxml
import lxml.etree

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


def add_del_iothread(params):
    """
       test API for addIOThread and delIOThread in class virDomain
    """

    logger = params['logger']
    fail = 0

    try:
        conn = libvirt.open(params['conn'])

        logger.info("get connection to libvirtd")
        guest = params['guestname']
        vm = conn.lookupByName(guest)
        logger.info("test guest name: %s" % guest)

        """ test effect guest running XML """
        if vm.isActive() == 1:
            logger.info("guest is running test with running guest")

            for i in range(300, 1000):
                if not find_iothreadid_fromxml(vm, 1, i):
                    logger.info("add iothread %d to running guest" % i)
                    vm.addIOThread(i, libvirt.VIR_DOMAIN_AFFECT_LIVE)
                    if find_iothreadid_fromxml(vm, 1, i):
                        vm.delIOThread(i, libvirt.VIR_DOMAIN_AFFECT_LIVE)
                        if find_iothreadid_fromxml(vm, 1, i):
                            logger.info("FAIL: still can find iothread id in XML")
                            fail = 1

                        break
                    else:
                        logger.info("FAIL: cannot find iothread id in XML")
                        fail = 1
                        break

        """ test effect guest config"""
        logger.info("test with guest inactive XML")
        for i in range(300, 1000):
            if not find_iothreadid_fromxml(vm, 0, i):
                logger.info("add iothread %d to guest config" % i)
                vm.addIOThread(i, libvirt.VIR_DOMAIN_AFFECT_CONFIG)
                if find_iothreadid_fromxml(vm, 0, i):
                    vm.delIOThread(i, libvirt.VIR_DOMAIN_AFFECT_CONFIG)
                    if find_iothreadid_fromxml(vm, 0, i):
                        logger.info("FAIL: still can find iothread id in XML")
                        fail = 1

                    break
                else:
                    logger.info("FAIL: cannot find iothread id in XML")
                    fail = 1
                    break

    except libvirtError as e:
        logger.error("API error message: %s" % e.message)
        fail = 1
    return fail
