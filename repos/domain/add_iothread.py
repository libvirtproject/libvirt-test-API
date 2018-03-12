#!/usr/bin/env python

import libvirt
from libvirt import libvirtError
import lxml
import lxml.etree

required_params = ('guestname', 'id',)
optional_params = {'conn': 'qemu:///system'}


def find_iothreadid_fromxml(vm, running, iothreadid):
    if (running == 1):
        tree = lxml.etree.fromstring(vm.XMLDesc(0))
    else:
        tree = lxml.etree.fromstring(vm.XMLDesc(libvirt.VIR_DOMAIN_XML_INACTIVE))

    set = tree.xpath("//iothreadids/iothread")
    for n in set:
        ids = n.attrib['id']
        if int(ids) == iothreadid:
            return True

    return False


def add_iothread(params):
    """
       test API for addIOThread in class virDomain
    """

    logger = params['logger']
    id = int(params['id'])

    try:
        conn = libvirt.open(params['conn'])

        logger.info("get connection to libvirtd")
        guest = params['guestname']
        vm = conn.lookupByName(guest)
        logger.info("test guest name: %s" % guest)

        """ test effect guest running XML """
        if vm.isActive() == 1:
            logger.info("guest is running test with running guest")
            if not find_iothreadid_fromxml(vm, 1, id):
                logger.info("add iothread %d to running guest" % id)
                vm.addIOThread(id, libvirt.VIR_DOMAIN_AFFECT_LIVE)
                if not find_iothreadid_fromxml(vm, 1, id):
                    logger.info("FAIL: cannot find iothread id in XML")
                    return 1
        else:
            """ test effect guest config"""
            logger.info("test with guest inactive XML")
            if not find_iothreadid_fromxml(vm, 0, id):
                logger.info("add iothread %d to guest config" % id)
                vm.addIOThread(id, libvirt.VIR_DOMAIN_AFFECT_CONFIG)
                if not find_iothreadid_fromxml(vm, 0, id):
                    logger.info("FAIL: cannot find iothread id in XML")
                    return 1

        logger.info("PASS: add iothread successful.")
    except libvirtError as e:
        logger.error("API error message: %s" % e.message)
        return 1
    return 0
