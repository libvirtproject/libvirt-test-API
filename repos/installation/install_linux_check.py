#!/usr/bin/env python
# Checking method for linux domain installation.

import os
import time
import libvirt

from src import sharedmod
from utils import utils

required_params = ('guestname', 'virt_type', 'hddriver', 'nicdriver',)
optional_params = {}

HOME_PATH = os.getcwd()


def install_linux_check(params):
    """check guest status after installation, including network ping,
       read/write option in guest. return value: 0 - ok; 1 - bad
    """
    global logger
    logger = params['logger']
    params.pop('logger')

    guestname = params.get('guestname')
    virt_type = params.get('virt_type')

    logger.info("the name of guest is %s" % guestname)

    # Connect to local hypervisor connection URI
    hypervisor = utils.get_hypervisor()

    logger.info("the type of hypervisor is %s" % hypervisor)

    conn = sharedmod.libvirtobj['conn']
    domobj = conn.lookupByName(guestname)
    state = domobj.info()[0]

    if(state == libvirt.VIR_DOMAIN_SHUTOFF):
        logger.info("guest is shutoff, if u want to run this case, \
                     guest must be started")
        return 1

    logger.info("get the mac address of vm %s" % guestname)
    mac = utils.get_dom_mac_addr(guestname)
    logger.info("the mac address of vm %s is %s" % (guestname, mac))

    timeout = 300
    while timeout:
        ipaddr = utils.mac_to_ip(mac, 180)
        if not ipaddr:
            logger.info(str(timeout) + "s left")
            time.sleep(10)
            timeout -= 10
        else:
            logger.info("the ip address of vm %s is %s" % (guestname, ipaddr))
            break

    if timeout == 0:
        logger.info("vm %s fail to get ip address" % guestname)
        return 1

    time.sleep(120)

    logger.info("Now checking guest health after installation")

    domain_name = guestname
    blk_type = params['hddriver']
    nic_type = params['nicdriver']
    Test_Result = 0

    # Ping guest from host
    logger.info("check point1: ping guest from host")
    if utils.do_ping(ipaddr, 20) == 1:
        logger.info("ping current guest successfull")
    else:
        logger.error("Error: can't ping current guest")
        Test_Result = 1
        return Test_Result

    # Creat file and read file in guest.
    logger.info("check point2: creat and read dirctory/file in guest")
    if utils.create_dir(ipaddr, "root", "redhat") == 0:
        logger.info("create dir - /tmp/test successfully")
        if utils.write_file(ipaddr, "root", "redhat") == 0:
            logger.info("write and read file: /tmp/test/test.log successfully")
        else:
            logger.error("Error: fail to write/read file - /tmp/test/test.log")
            Test_Result = 1
            return Test_Result
    else:
        logger.error("Error: fail to create dir - /tmp/test")
        Test_Result = 1
        return Test_Result

    # Check whether vcpu equals the value set in guest config xml
    logger.info("check point3: check cpu number in guest equals to \
                 the value set in domain config xml")
    vcpunum_expect = int(utils.get_num_vcpus(domain_name))
    logger.info("vcpu number in domain config xml - %s is %s" %
                (domain_name, vcpunum_expect))
    vcpunum_actual = int(utils.get_remote_vcpus(ipaddr, "root", "redhat"))
    logger.info("The actual vcpu number in guest - %s is %s" %
                (domain_name, vcpunum_actual))
    if vcpunum_expect == vcpunum_actual:
        logger.info("The actual vcpu number in guest is \
                     equal to the setting your domain config xml")
    else:
        logger.error("Error: The actual vcpu number in guest is \
                      NOT equal to the setting your domain config xml")
        Test_Result = 1
        return Test_Result

    # Check whether mem in guest is equal to the value set in domain config xml
    if not utils.isPower():
        logger.info("check point4: check whether mem in guest is equal to \
                    the value set in domain config xml")
        mem_expect = int(utils.get_size_mem(domain_name))
        logger.info("current mem size in domain config xml - %s is %s" %
                    (domain_name, mem_expect))
        cmd = "dmidecode -t 17 | awk -F: '/Size/ {print $2}'"
        out = utils.remote_exec_pexpect(ipaddr, "root", "redhat", cmd)
        if out[0]:
            logger.error("CMD failed: %s, out: %s" % (cmd, out[1]))
            return 1

        mem_actual = int(out[1].split(" ")[0]) * 1024
        logger.info("The actual mem size in guest - %s is %s" %
                    (domain_name, mem_actual))
        if mem_expect == mem_actual:
            logger.info("The actual mem size in guest is equal to the\
                        setting your domain config xml")
        else:
            logger.error("Error: The actual mem size in guest is NOT equal to \
                          the setting your domain config xml")
            Test_Result = 1
            return Test_Result

    # Check nic and blk driver in guest
    if 'kvm' in virt_type or 'xenfv' in virt_type:
        logger.info("check point5: check nic and blk driver in guest is \
                     expected as your config:")
        if utils.validate_remote_nic_type(ipaddr, "root", "redhat",
                                          nic_type, logger) == 0 and \
           utils.validate_remote_blk_type(ipaddr, "root", "redhat",
                                          blk_type, logger) == 0:
            logger.info("nic type - %s and blk type - %s check successfully" %
                        (nic_type, blk_type))
        else:
            logger.error("Error: nic type - %s or blk type - %s check failed" %
                         (nic_type, blk_type))
            Test_Result = 1
            return Test_Result

    return Test_Result
