#!/usr/bin/env python
import libvirt
from libvirt import libvirtError
from utils import utils

required_params = ('guestname',)
optional_params = {'conn': 'qemu:///system'}

ONLINE_CPU = '/sys/devices/system/cpu/online'
CGROUP_PERCPU = '/sys/fs/cgroup/cpuacct/machine.slice/machine-qemu\\x2d%s.scope/cpuacct.usage_percpu'
CGROUP_PERVCPU = '/sys/fs/cgroup/cpuacct/machine.slice/machine-qemu\\x2d%s.scope/vcpu%d/cpuacct.usage_percpu'
CGROUP_USAGE = '/sys/fs/cgroup/cpuacct/machine.slice/machine-qemu\\x2d%s.scope/cpuacct.usage'
CGROUP_STAT = '/sys/fs/cgroup/cpuacct/machine.slice/machine-qemu\\x2d%s.scope/cpuacct.stat'


def getcputime(a):
    return open(a[0]).read().split()[a[1]]


def virtgetcputime(a):
    return a[0].getCPUStats(0)[a[1]][a[2]]


def getvcputime(a):
    ret = 0
    for i in range(int(a[0])):
        ret += int(open(CGROUP_PERVCPU % (a[1], i)).read().split()[a[2]])

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
    fail = 0

    cpu = utils.file_read(ONLINE_CPU)
    logger.info("host online cpulist is %s" % cpu)

    cpu_tuple = utils.param_to_tuple_nolength(cpu)
    if not cpu_tuple:
        logger.info("error in function param_to_tuple_nolength")
        return 1

    try:
        conn = libvirt.open(params['conn'])

        logger.info("get connection to libvirtd")
        guest = params['guestname']
        vm = conn.lookupByName(guest)
        vcpus = vm.info()[3]
        for n in range(len(cpu_tuple)):
            if not cpu_tuple[n]:
                continue

            D = utils.get_standard_deviation(getcputime, virtgetcputime,
                                             [CGROUP_PERCPU % guest, n], [vm, n, 'cpu_time'])
            logger.info("Standard Deviation for host cpu %d cputime is %d" % (n, D))

            """ expectations 403423 is a average collected in a x86_64 low load machine"""
            if D > 403423 * 5:
                fail = 1
                logger.info("FAIL: Standard Deviation is too big \
                             (biger than %d) for host cpu %d" % (403423 * 5, n))

            D = utils.get_standard_deviation(getvcputime, virtgetcputime,
                                             [vcpus, guest, n], [vm, n, 'vcpu_time'])
            logger.info("Standard Deviation for host cpu %d vcputime is %d" % (n, D))

            """ expectations 4034 is a average collected in a x86_64 low load machine"""
            if D > 4034 * 5 * vcpus:
                fail = 1
                logger.info("FAIL: Standard Deviation is too big \
                             (biger than %d) for host cpu time %d" % (4034 * 5 * vcpus, n))

        D = utils.get_standard_deviation(getcputime, virtgettotalcputime,
                                         [CGROUP_USAGE % guest, 0], [vm, 'cpu_time'])
        logger.info("Standard Deviation for host cpu total cputime is %d" % D)

        """ expectations 313451 is a average collected in a x86_64 low load machine"""
        if D > 313451 * 5 * len(cpu_tuple):
            fail = 1
            logger.info("FAIL: Standard Deviation is too big \
                         (biger than %d) for host cpu time %d" % (313451 * 5 * len(cpu_tuple), n))

        D = utils.get_standard_deviation(getcputime, virtgettotalcputime2,
                                         [CGROUP_STAT % guest, 3], [vm, 'system_time'])
        logger.info("Standard Deviation for host cpu total system time is %d" % D)

        """ expectations 10 is a average collected in a x86_64 low load machine"""
        if D > 10 * 5:
            fail = 1
            logger.info("FAIL: Standard Deviation is too big \
                         (biger than %d) for host system cpu time %d" % (10 * 5, n))

        D = utils.get_standard_deviation(getcputime, virtgettotalcputime2,
                                         [CGROUP_STAT % guest, 1], [vm, 'user_time'])
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
