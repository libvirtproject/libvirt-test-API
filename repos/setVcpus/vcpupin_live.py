#!/usr/bin/env python
# Test domain vcpu pin with flag VIR_DOMAIN_AFFECT_LIVE, check
# vcpu subprocess status under domain task list on host.

import re

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('guestname', 'vcpu', 'cpulist',)
optional_params = {}


def vcpupin_check(guestname, vcpu, cpulist):
    """check vcpu subprocess status of the running virtual machine
       grep Cpus_allowed_list /proc/PID/task/*/status
    """
    cmd_pid = "cat /var/run/libvirt/qemu/%s.pid" % guestname
    status, pid = utils.exec_cmd(cmd_pid, shell=True)
    if status:
        logger.error("failed to get the pid of domain %s" % guestname)
        return 1

    cmd_vcpu_task_id = "virsh qemu-monitor-command %s --hmp info cpus|grep '#%s'|cut -d '=' -f3"\
        % (guestname, vcpu)
    status, vcpu_task_id = utils.exec_cmd(cmd_vcpu_task_id, shell=True)
    if status:
        logger.error("failed to get the threadid of domain %s" % guestname)
        return 1

    logger.debug("vcpu id %s:" % vcpu_task_id[0])
    cmd_cpus_allowed_list = "grep Cpus_allowed_list /proc/%s/task/%s/status" % (pid[0], vcpu_task_id[0])
    status, output = utils.exec_cmd(cmd_cpus_allowed_list, shell=True)
    if status:
        logger.error("failed to get the cpu_allowed_list of vcpu %s")
        return 1

    logger.debug("the output of command 'grep Cpus_allowed_list \
                          /proc/%s/task/%s/status' is %s" % (pid[0], vcpu_task_id[0], output))

    if output[0].split('\t')[1] == cpulist:
        logger.info("vcpu process cpus allowed list is expected")
        return 0
    else:
        logger.error("vcpu process cpus allowed list is not expected")
        return 1


def vcpupin_live(params):
    """pin domain vcpu to host cpu with live flag
    """
    global logger
    logger = params['logger']
    params.pop('logger')
    guestname = params['guestname']
    vcpu = int(params['vcpu'])
    cpulist = params['cpulist']

    logger.info("the name of virtual machine is %s" % guestname)
    logger.info("the given vcpu is %s" % vcpu)
    logger.info("the given cpulist is %s" % cpulist)

    global maxcpu
    maxcpu = utils.get_host_cpus()
    logger.info("%s physical cpu on host" % maxcpu)

    conn = sharedmod.libvirtobj['conn']

    try:
        domobj = conn.lookupByName(guestname)
        cpumap = utils.param_to_tuple(cpulist, maxcpu)
        if not cpumap:
            logger.error("cpulist: Invalid format")
            return 1

        logger.debug("cpumap for vcpu pin is:")
        logger.debug(cpumap)

        logger.info("pin domain vcpu %s to host cpu %s with flag: %s" %
                    (vcpu, cpulist, libvirt.VIR_DOMAIN_AFFECT_LIVE))
        domobj.pinVcpuFlags(vcpu, cpumap, libvirt.VIR_DOMAIN_AFFECT_LIVE)

        logger.info("check vcpus info")
        ret = domobj.vcpus()
        logger.debug("vcpus info is:")
        logger.debug(ret)
        if ret[1][vcpu] == cpumap:
            logger.info("vcpus info is expected")
        else:
            logger.error("vcpus info is not expected")
            return 1

    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    logger.info("check vcpu pin status on host")
    ret = vcpupin_check(guestname, vcpu, cpulist)
    if ret:
        logger.error("domain vcpu pin failed")
        return 1
    else:
        logger.info("domain vcpu pin succeed")
        return 0
