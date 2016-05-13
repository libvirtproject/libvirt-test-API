#!/usr/bin/env python
""" Query or change the pinning of domain's emulator threads to
  host physical CPUs."""


import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('guestname', 'cpulist',)
optional_params = {}


def check_pinemulator(guestname, maxcpu, pininfo_after):
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
    pininfo_in_process = str(utils.param_to_tuple(cpulistcheck, maxcpu))

    if cmp(pininfo_in_process, pininfo_after):
        logger.error("domain emulator pin failed")
        return 1
    else:
        logger.info("domain emulator pin successed")
        return 0


def pinemulator(params):
    """Dynamically change the real CPUs which can be allocated to the
       emulator process of a domain. This function requires privileged
       access to the hypervisor. """
    global logger
    logger = params['logger']
    guestname = params['guestname']
    cpulist = params['cpulist']

    logger.info("the name of virtual machine is %s" % guestname)
    logger.info("the given cpulist is %s" % cpulist)

    maxcpu = utils.get_host_cpus()
    logger.info("%s physical cpu on host" % maxcpu)

    cpumap = utils.param_to_tuple(cpulist, maxcpu)
    if not cpumap:
        logger.error("cpulist: Invalid format")
        return 1

    conn = sharedmod.libvirtobj['conn']

    try:
        domobj = conn.lookupByName(guestname)

        pininfo_original = str(domobj.emulatorPinInfo())
        logger.info("the original emulator pin of the domain is: %s" %
                    pininfo_original)

        logger.info("pin domain emulator to host cpu %s" % cpulist)
        domobj.pinEmulator(cpumap)

        pininfo_after = str(domobj.emulatorPinInfo())
        logger.info("the revised emulator pin of the domain is: %s" %
                    pininfo_after)

        ret = check_pinemulator(guestname, maxcpu, pininfo_after)
        return ret

    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return 1
