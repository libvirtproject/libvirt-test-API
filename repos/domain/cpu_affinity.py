#!/usr/bin/env python
# To test domain CPU affinity

import time
import math

from xml.dom import minidom
from libvirt import libvirtError

from src import sharedmod
from utils import utils, process

required_params = ('guestname', 'vcpu',)
optional_params = {}


def redefine_vcpu_number(domobj, domain_name, vcpu):
    """dump domain xml description to change the vcpu number,
       then, define the domain again
    """
    guestxml = domobj.XMLDesc(0)
    logger.debug('''original guest %s xml :\n%s''' % (domain_name, guestxml))

    doc = minidom.parseString(guestxml)

    newvcpu = doc.createElement('vcpu')
    newvcpuval = doc.createTextNode(vcpu)
    newvcpu.appendChild(newvcpuval)

    domain = doc.getElementsByTagName('domain')[0]
    oldvcpu = doc.getElementsByTagName('vcpu')[0]

    domain.replaceChild(newvcpu, oldvcpu)

    return doc.toxml()


def set_vcpus(domobj, domain_name, vcpu):
    """set the value of virtual machine to vcpu offline , then boot up
       the virtual machine
    """
    timeout = 60
    logger.info('destroy domain')

    logger.info("get the mac address of vm %s" % domain_name)
    mac = utils.get_dom_mac_addr(domain_name)
    logger.info("the mac address of vm %s is %s" % (domain_name, mac))

    logger.info("get ip by mac address")
    ip = utils.mac_to_ip(mac, 180)
    logger.info("the ip address of vm %s is %s" % (domain_name, ip))

    try:
        domobj.destroy()
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("fail to destroy domain")
        return 1

    while timeout:
        time.sleep(10)
        timeout -= 10
        logger.info(str(timeout) + "s left")

        logger.info('ping guest')

        if utils.do_ping(ip, 30):
            logger.error('The guest is still active, IP: ' + str(ip))
        else:
            logger.info("domain %s is destroied successfully" % domain_name)
            break

    if timeout <= 0:
        logger.error("the domain couldn't be destroied within 60 secs.")
        return 1

    newguestxml = redefine_vcpu_number(domobj, domain_name, vcpu)
    logger.debug('''new guest %s xml :\n%s''' % (domain_name, newguestxml))

    logger.info("undefine the original guest")
    try:
        domobj.undefine()
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("fail to undefine guest %s" % domain_name)
        return 1

    logger.info("define guest with new xml")
    try:
        conn = domobj._conn
        conn.defineXML(newguestxml)
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("fail to define guest %s" % domain_name)
        return 1

    try:
        logger.info('boot guest up ...')
        domobj.create()
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("fail to start domain %s" % domain_name)
        return 1

    timeout = 600

    while timeout:
        time.sleep(10)
        timeout -= 10

        ip = utils.mac_to_ip(mac, 180)

        if not ip:
            logger.info(str(timeout) + "s left")
        else:
            logger.info("vm %s power on successfully" % domain_name)
            logger.info("the ip address of vm %s is %s" % (domain_name, ip))
            break

    if timeout <= 0:
        logger.info("fail to power on vm %s" % domain_name)
        return 1

    return 0


def vcpu_affinity_check(domain_name, vcpu, expected_pinned_cpu, hypervisor):
    """check the task in the process of the running virtual machine
       grep Cpus_allowed_list /proc/PID/task/*/status
    """
    major, minor = utils.get_version()
    if 'qemu' in hypervisor:
        cmd = "cat /var/run/libvirt/qemu/%s.pid" % domain_name
        ret = process.run(cmd, shell=True, ignore_status=True)
        if ret.exit_status:
            logger.error("failed to get the pid of \
                          the running virtual machine process")
            return 1
        pid = ret.stdout
        if int(major) > 5:
            cmd = "rpm -q qemu-kvm-rhev"
            ret = process.run(cmd, shell=True, ignore_status=True)
            if int(minor) == 8 or (int(major) == 7 and int(minor) == 6 and not ret.exit_status):
                cmd = ("virsh qemu-monitor-command %s --hmp info cpus|grep '#%s'|cut -d '=' -f2"
                       % (domain_name, vcpu))
            else:
                cmd = ("virsh qemu-monitor-command %s --hmp info cpus|grep '#%s'|cut -d '=' -f3"
                       % (domain_name, vcpu))
            ret = process.run(cmd, shell=True, ignore_status=True)
            vcpu_task_id = ret.stdout
            logger.debug("vcpu id %s:" % vcpu_task_id)

            cmd = "grep Cpus_allowed_list /proc/%s/task/%s/status" % (pid, vcpu_task_id)
            ret = process.run(cmd, shell=True, ignore_status=True)
            logger.debug("the output of command 'grep Cpus_allowed_list \
                          /proc/%s/task/%s/status' is %s" % (pid, vcpu_task_id, ret.stdout))
            actual_pinned_cpu = int(ret.stdout.split('\t')[1])
        elif int(major) == 5:
            cmd = "grep Cpus_allowed /proc/%s/task/*/status" % pid
            ret = process.run(cmd, shell=True, ignore_status=True)
            logger.debug("the output of command 'grep Cpus_allowed \
                          /proc/%s/task/*/status' is %s" % (pid, ret.stdout))
            task_list = ret.stdout.split('\n')[2:]
            vcpu_task = task_list[int(vcpu)]
            tmp = int(vcpu_task.split('\t')[1].split(',')[-1])
            actual_pinned_cpu = math.log(tmp, 2)
        else:
            logger.error("unsupported host os version: %s.%s" % (major, minor))
            return 1
    elif 'xen' in hypervisor:
        cmd = "virsh vcpuinfo %s|grep -1 ^VCPU.*[^0-9]%s$|tail -1|cut -d: -f2" % (domain_name, vcpu)
        ret = process.run(cmd, shell=True, ignore_status=True)
        actual_pinned_cpu = int(ret.stdout)
    else:
        logger.info("unsupported hypervisor type: %s" % hypervisor)
        return 1
    logger.info("the actual pinned cpu is %s" % actual_pinned_cpu)
    cmd = "virsh vcpuinfo %s" % domain_name
    ret = process.run(cmd, shell=True, ignore_status=True)
    logger.debug("after pinning, the vcpu status is %s" % ret.stdout)

    if actual_pinned_cpu == expected_pinned_cpu:
        logger.info("actual_pinned_physical_cpu is \
                     equal to expected_pinned_physical_cpu")
        return 0
    else:
        logger.info("actual_pinned_physical_cpu is \
                     not equal to expected_pinned_physical_cpu")
        return 1


def cpu_affinity(params):
    """set vcpu of virtual machine to value of parameter vcpu
       call libvirt API function to set cpu affinity
       check the result after cpupin
    """
    global logger
    logger = params['logger']
    params.pop('logger')
    domain_name = params['guestname']
    vcpu = params['vcpu']

    if utils.isPower():
        logger.info("This case need update for ppc arch.")
        return 0

    logger.info("the name of virtual machine is %s" % domain_name)
    logger.info("the vcpu given is %s" % vcpu)

    conn = sharedmod.libvirtobj['conn']
    uri = conn.getURI()
    hypervisor = uri.split(':')[0]

    # Get cpu affinity
    guest_names = []
    ids = conn.listDomainsID()
    for id in ids:
        obj = conn.lookupByID(id)
        guest_names.append(obj.name())

    if domain_name not in guest_names:
        logger.error("guest %s doesn't exist or not be running." %
                     domain_name)
        return 1

    domobj = conn.lookupByName(domain_name)

    vcpunum = utils.get_num_vcpus(domain_name)
    logger.info("the current vcpu number of guest %s is %s" %
                (domain_name, vcpunum))

    if vcpunum != vcpu:
        logger.info("set the vcpu of the guest to %s" % vcpu)
        ret = set_vcpus(domobj, domain_name, vcpu)
        if ret != 0:
            return 1

    vcpunum_after_set = utils.get_num_vcpus(domain_name)
    logger.info("after setting, the current vcpu number the guest is %s" %
                vcpunum_after_set)
    vcpu_list = list(range(int(vcpunum_after_set)))

    physical_cpu_num = utils.get_host_cpus()
    logger.info("in the host, we have %s physical cpu" % physical_cpu_num)

    cpu_affinity = ()
    for i in range(physical_cpu_num):
        cpu_affinity = cpu_affinity + (False,)

    cmd = "lscpu | grep 'POWER8'"
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status:
        cpu_power8 = False
    else:
        cpu_power8 = True

    retflag = 0
    for i in range(physical_cpu_num):
        cpu_affinity_test = ()
        for affinity_num in range(len(cpu_affinity)):
            if affinity_num == i:
                cpu_affinity_test = cpu_affinity_test + (True,)
            else:
                cpu_affinity_test = cpu_affinity_test + \
                    (cpu_affinity[affinity_num],)

        logger.debug("the data for testing is")
        logger.debug(cpu_affinity_test)

        for vcpu_pinned in vcpu_list:
            try:
                logger.info("Now, we pin vcpu %s to physical vcpu %s" %
                            (vcpu_pinned, i))

                cmd = "virsh vcpuinfo %s" % domain_name
                ret = process.run(cmd, shell=True, ignore_status=True)
                logger.debug("before pinning, the vcpu status is %s" % ret.stdout[1])

                domobj.pinVcpu(vcpu_pinned, cpu_affinity_test)
            except libvirtError as e:
                logger.error("API error message: %s, error code is %s"
                             % (e.get_error_message(), e.get_error_code()))
                logger.error("fail to vcpupin domain")
                return 1

            ret = vcpu_affinity_check(domain_name, vcpu_pinned, i, hypervisor)
            retflag = retflag + ret
            if ret:
                logger.error("vcpu affinity checking failed.")
            else:
                logger.info("vcpu affinity checking successed.")
        if cpu_power8:
            i = i + 8
        else:
            i = i + 1

    if retflag:
        return 1
    return 0
