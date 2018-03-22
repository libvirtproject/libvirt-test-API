#!/usr/bin/env python

import libvirt
from libvirt import libvirtError
import lxml
import lxml.etree

required_params = ('guestname',)
optional_params = {'conn': 'qemu:///system'}


def get_period_fromxml(vm, running):
    if (running == 1):
        tree = lxml.etree.fromstring(vm.XMLDesc(0))
    else:
        tree = lxml.etree.fromstring(
            vm.XMLDesc(libvirt.VIR_DOMAIN_XML_INACTIVE))

    set = tree.xpath("//memballoon/stats")
    if len(set) == 0:
        return 0
    for n in set:
        period = n.attrib['period']
        return period


def check_memoryStats(vm):
    memstats = vm.memoryStats()
    try:
        available = memstats["available"]
        if available:
            logger.info("can get available from memoryStats()")
            return 0
    except KeyError:
        logger.info("cannot get available from memoryStats()")
        return 1


def set_memory_period(params):
    """
       test API for setMemoryStatsPeriod in class virDomain
    """
    global logger
    logger = params['logger']
    fail = 0

    try:
        conn = libvirt.open(params['conn'])

        logger.info("get connection to libvirtd")
        guest = params['guestname']
        vm = conn.lookupByName(guest)
        logger.info("test guest name: %s" % guest)

        """ test with running vm """
        if vm.isActive() == 1:
            logger.info("guest is running, test with running guest")
            period = int(get_period_fromxml(vm, 1))
            if period == 0:
                vm.setMemoryStatsPeriod(1, libvirt.VIR_DOMAIN_AFFECT_LIVE)
                if int(get_period_fromxml(vm, 1)) != 1:
                    logger.error("Period value from xml is not right")
                    fail = 1
                elif check_memoryStats(vm) == 0:
                    period = 1
                else:
                    fail = 1

            if period > 0:
                if check_memoryStats(vm) == 0:
                    vm.setMemoryStatsPeriod(
                        period + 1, libvirt.VIR_DOMAIN_AFFECT_LIVE)
                    if int(get_period_fromxml(vm, 1)) != period + 1:
                        logger.error("Period value from xml is not right")
                        fail = 1
                else:
                    fail = 1

        """ test with vm config """
        logger.info("guest is not running, test with config")
        period = int(get_period_fromxml(vm, 0))
        vm.setMemoryStatsPeriod(period + 1, libvirt.VIR_DOMAIN_AFFECT_CONFIG)
        if int(get_period_fromxml(vm, 0)) != period + 1:
            logger.error("Period value from xml is not right")
            fail = 1

    except libvirtError as e:
        logger.error("API error message: %s" % e.get_error_message())
        fail = 1
    return fail
