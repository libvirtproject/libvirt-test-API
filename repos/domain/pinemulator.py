#!/usr/bin/env python
""" Query or change the pinning of domain's emulator threads to
  host physical CPUs."""

from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('guestname', 'cpulist',)
optional_params = {}


def check_pinemulator(guestname, maxcpu, pininfo_after, logger):
    """check emulator status of the running virtual machine
    """

    cmd = "cat /var/run/libvirt/qemu/%s.pid" % guestname
    status, pid = utils.exec_cmd(cmd, shell=True)
    if status:
        logger.error("failed to get the pid of domain %s" % guestname)
        return 1

    cmd = "grep Cpus_allowed_list /proc/%s/task/%s/status" % (pid[0], pid[0])
    status, output = utils.exec_cmd(cmd, shell=True)
    if status:
        logger.error("failed to get Cpus_allowed_list")
        return 1

    cpu_allowed_list = output[0]
    cpulistcheck = cpu_allowed_list.split('\t')[1]
    pininfo_in_process = utils.param_to_tuple(cpulistcheck, maxcpu)

    if len(pininfo_in_process) == len(pininfo_after):
        for index in range(len(pininfo_in_process)):
            if pininfo_in_process[index] != pininfo_after[index]:
                logger.error("FAIL: pin don't equal. %s" % index)
                return 1
    else:
        logger.error("FAIL: pin length don't equal.")
        return 1

    logger.info("PASS: domain emulator pin successed")
    return 0


def pinemulator(params):
    """Dynamically change the real CPUs which can be allocated to the
       emulator process of a domain. This function requires privileged
       access to the hypervisor. """
    logger = params['logger']
    guestname = params['guestname']
    cpulist = params['cpulist']

    logger.info("the name of virtual machine is %s" % guestname)
    logger.info("the given cpulist is %s" % cpulist)

    conn = sharedmod.libvirtobj['conn']
    if utils.isPower():
        maxcpu = conn.getMaxVcpus('kvm')
    else:
        maxcpu = utils.get_host_cpus()
    logger.info("%s physical cpu on host" % maxcpu)

    cpumap = utils.param_to_tuple(cpulist, maxcpu)
    if not cpumap:
        logger.error("cpulist: Invalid format")
        return 1



    try:
        domobj = conn.lookupByName(guestname)

        pininfo_original = domobj.emulatorPinInfo()
        logger.info("the original emulator pin of the domain is: %s" %
                    str(pininfo_original))

        logger.info("pin domain emulator to host cpu %s" % cpulist)
        domobj.pinEmulator(cpumap)

        pininfo_after = domobj.emulatorPinInfo()
        logger.info("the revised emulator pin of the domain is: %s" %
                    str(pininfo_after))

        ret = check_pinemulator(guestname, maxcpu, pininfo_after, logger)
        return ret

    except libvirtError as e:
        logger.error("libvirt call failed: " + e.get_error_message())
        return 1
