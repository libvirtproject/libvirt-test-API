#!/usr/bin/env python

import libvirt
import libvirt_qemu
from libvirt import libvirtError
import lxml
import lxml.etree
import json
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


def find_iothreadpin_fromxml(vm, running, iothreadid):
    if (running == 1):
        tree = lxml.etree.fromstring(vm.XMLDesc(0))
    else:
        tree = lxml.etree.fromstring(
            vm.XMLDesc(libvirt.VIR_DOMAIN_XML_INACTIVE))

    set = tree.xpath("//cputune/iothreadpin")
    for n in set:
        ids = n.attrib["iothread"]
        cpuset_xml = n.attrib["cpuset"]
        if int(ids) == iothreadid:
            logger.info("cpuset in xml is %s" % cpuset_xml)
            return cpuset_xml

    return False


def get_qmp_return_iothread(string, iothreadid):
    js = json.loads(string)

    try:
        js['return']
        err = False
    except KeyError:
        try:
            js['error']
            err = True
        except KeyError:
            error = "invalid string"
            return False

    if not err:
        for n in js['return']:
            if n['id'] == ("iothread%d" % iothreadid):
                return int(n['thread-id'])
        logger.info("cannot find iothread in query-iothreads return")
        return False

    else:
        logger.info("qmp command get failed: %s" % js['error']['desc'])
        return False


def check_iothreadpin(vm, iothreadid, cpuset):
    ret = libvirt_qemu.qemuMonitorCommand(
        vm, '{ "execute": "query-iothreads" }', 0)
    tid = get_qmp_return_iothread(ret, iothreadid)
    if not tid:
        return False

    cmds = "taskset --cpu-list -p %d| awk {'print $6'}" % tid
    (status, output) = utils.exec_cmd(cmds, shell=True)
    if status != 0:
        logger.info("Exec_cmd failed: %s" % cmds)
        return False

    logger.info("cpuset from taskset is %s" % output[0])
    if output[0] != cpuset:
        logger.info(
            "Cpuset is not equal: taskset is %s and libvirt is %s" %
            (output, cpuset))
        return False

    return True


def pin_iothread(params):
    """
       test API for pinIOThread in class virDomain
    """

    global logger
    logger = params['logger']
    fail = 0

    try:
        conn = libvirt.open(params['conn'])

        logger.info("get connection to libvirtd")
        guest = params['guestname']
        vm = conn.lookupByName(guest)
        hostcpu = utils.get_host_cpus()
        tu_cpu = ()
        logger.info("test guest name: %s" % guest)

        for i in range(hostcpu):
            if i % 2 == 0:
                tu_cpu += (1,)
            else:
                tu_cpu += (0,)

        """ test effect a running guest"""
        if vm.isActive() == 1:
            logger.info("guest is running test with running guest")

            if not find_iothreadid_fromxml(vm, 1, 1):
                logger.info("add iothread %d to running guest" % 1)
                vm.addIOThread(1, libvirt.VIR_DOMAIN_AFFECT_LIVE)

            vm.pinIOThread(1, tu_cpu, libvirt.VIR_DOMAIN_AFFECT_LIVE)
            cpuset = find_iothreadpin_fromxml(vm, 1, 1)
            if cpuset:
                if not check_iothreadpin(vm, 1, cpuset):
                    fail = 1
                tmp_cpuset = utils.param_to_tuple(cpuset, hostcpu)
                if not tmp_cpuset:
                    fail = 1
                elif tmp_cpuset != tu_cpu:
                    logger.info("FAIL: the cpuset in xml is not equal the cpuset we set")
                    fail = 1
            else:
                logger.info("FAIL: cannot find iothreadpin in XML")
                fail = 1

        """ test effect guest config"""
        logger.info("test with guest inactive XML")
        if not find_iothreadid_fromxml(vm, 0, 1):
            logger.info("add iothread 1 to guest config")
            vm.addIOThread(1, libvirt.VIR_DOMAIN_AFFECT_CONFIG)

        vm.pinIOThread(1, tu_cpu, libvirt.VIR_DOMAIN_AFFECT_LIVE)
        cpuset = find_iothreadpin_fromxml(vm, 1, 1)
        if cpuset:
            tmp_cpuset = utils.param_to_tuple(cpuset, hostcpu)
            if not tmp_cpuset:
                fail = 1
            elif tmp_cpuset != tu_cpu:
                logger.info("FAIL: the cpuset in xml is not equal the cpuset we set")
                fail = 1
        else:
            logger.info("FAIL: cannot find iothreadpin in XML")
            fail = 1

    except libvirtError as e:
        logger.error("API error message: %s" % e.message)
        fail = 1
    return fail
