#!/usr/bin/env python
import os
import re
import libvirt
from libvirt import libvirtError
from utils import utils

required_params = ('guestname',)
optional_params = {'conn': 'qemu:///system'}

ONLINE_CPU = '/sys/devices/system/cpu/online'

CGROUP_PERCPU = 'cpuacct.usage_percpu'
CGROUP_PERVCPU = 'vcpu%d/cpuacct.usage_percpu'
CGROUP_USAGE = 'cpuacct.usage'
CGROUP_STAT = 'cpuacct.stat'
CGROUP_PATH = '/sys/fs/cgroup/cpuacct/machine.slice/'
CGROUP_RE = 'machine-qemu.*?%s.scope'


def get_cpu_path(guestname, logger):
    for path in os.listdir(CGROUP_PATH):
        logger.info("Check" + path)
        logger.info("Check" + CGROUP_RE % guestname)
        if re.match(CGROUP_RE % guestname, path):
            return CGROUP_PATH + path + "/"
        if re.match(CGROUP_RE % guestname.replace('_', ''), path):
            return CGROUP_PATH + path + "/"
    return False


def getcputime(a):
    return open(a[0]).read().split()[a[1]]


def virtgetcputime(a):
    return a[0].getCPUStats(0)[a[1]][a[2]]


def getvcputime(a):
    ret = 0
    for i in range(int(a[0])):
        ret += int(open(a[1] + CGROUP_PERVCPU % i).read().split()[a[2]])

    return ret


def virtgettotalcputime(a):
    return a[0].getCPUStats(1)[0][a[1]]


def virtgettotalcputime2(a):
    return a[0].getCPUStats(1)[0][a[1]] / 10000000


def cpu_status(params):
    """
       test API for getCPUStats in class virDomain
    """
    logger = params['logger']
    guest = params['guestname']

    fail = 0

    cpu = utils.file_read(ONLINE_CPU)
    logger.info("host online cpulist is %s" % cpu)

    cpu_path = get_cpu_path(guest, logger)
    if not cpu_path:
        logger.error("Can't find cgroup path.")
        return 1
    cpu_tuple = utils.param_to_tuple_nolength(cpu)
    if not cpu_tuple:
        logger.info("error in function param_to_tuple_nolength")
        return 1

    try:
        conn = libvirt.open(params['conn'])

        logger.info("get connection to libvirtd")
        vm = conn.lookupByName(guest)
        vcpus = vm.info()[3]
        for n in range(len(cpu_tuple)):
            if not cpu_tuple[n]:
                continue

            D = utils.get_standard_deviation(getcputime, virtgetcputime,
                                             [cpu_path + CGROUP_PERCPU, n], [vm, n, 'cpu_time'])
            logger.info("Standard Deviation for host cpu %d cputime is %d" % (n, D))

            """ expectations 403423 is a average collected in a x86_64 low load machine"""
            if D > 403423 * 5:
                fail = 1
                logger.info("FAIL: Standard Deviation is too big \
                             (biger than %d) for host cpu %d" % (403423 * 5, n))

            D = utils.get_standard_deviation(getvcputime, virtgetcputime,
                                             [vcpus, cpu_path, n], [vm, n, 'vcpu_time'])
            logger.info("Standard Deviation for host cpu %d vcputime is %d" % (n, D))

            """ expectations 4034 is a average collected in a x86_64 low load machine"""
            if D > 4034 * 5 * vcpus:
                fail = 1
                logger.info("FAIL: Standard Deviation is too big \
                             (biger than %d) for host cpu time %d" % (4034 * 5 * vcpus, n))

        D = utils.get_standard_deviation(getcputime, virtgettotalcputime,
                                         [cpu_path + CGROUP_USAGE, 0], [vm, 'cpu_time'])
        logger.info("Standard Deviation for host cpu total cputime is %d" % D)

        """ expectations 313451 is a average collected in a x86_64 low load machine"""
        if D > 313451 * 5 * len(cpu_tuple):
            fail = 1
            logger.info("FAIL: Standard Deviation is too big \
                         (biger than %d) for host cpu time %d" % (313451 * 5 * len(cpu_tuple), n))

        D = utils.get_standard_deviation(getcputime, virtgettotalcputime2,
                                         [cpu_path + CGROUP_STAT, 3], [vm, 'system_time'])
        logger.info("Standard Deviation for host cpu total system time is %d" % D)

        """ expectations 10 is a average collected in a x86_64 low load machine"""
        if D > 10 * 5:
            fail = 1
            logger.info("FAIL: Standard Deviation is too big \
                         (biger than %d) for host system cpu time %d" % (10 * 5, n))

        D = utils.get_standard_deviation(getcputime, virtgettotalcputime2,
                                         [cpu_path + CGROUP_STAT, 1], [vm, 'user_time'])
        logger.info("Standard Deviation for host cpu total user time is %d" % D)

        """ expectations 10 is a average collected in a x86_64 low load machine"""
        if D > 10 * 5:
            fail = 1
            logger.info("FAIL: Standard Deviation is too big \
                         (biger than %d) for host user cpu time %d" % (10 * 5, n))

    except libvirtError as e:
        logger.error("API error message: %s" % e.message)
        fail = 1
    return fail
