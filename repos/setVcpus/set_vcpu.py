#!/usr/bin/env python
# Test enables/disables individual vcpus

from xml.dom import minidom

from libvirt import libvirtError
from utils import utils
from src import sharedmod

required_params = ('guestname', 'vcpulist', 'state')
optional_params = {}


def get_vcpu_number(domobj, logger):
    """dump domain config xml description to get vcpu number, return
       current vcpu and maxvcpu
    """
    try:
        guestxml = domobj.XMLDesc(0)
        logger.debug("domain %s xml is :\n%s" % (domobj.name(), guestxml))
        xml = minidom.parseString(guestxml)
        vcpu = xml.getElementsByTagName('vcpu')[0]
        maxvcpu = int(vcpu.childNodes[0].data)
        logger.info("domain max vcpu number is: %s" % maxvcpu)

        if vcpu.hasAttribute('current'):
            attr = vcpu.getAttributeNode('current')
            current = int(attr.nodeValue)
        else:
            logger.info("no 'current' atrribute for element vcpu")
            current = int(vcpu.childNodes[0].data)

        logger.info("domain current vcpu number is: %s" % current)

    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return False

    return current, maxvcpu


def set_vcpu(params):
    """Enables/disables individual vcpus described by @vcpumap in the hypervisor
    """
    logger = params['logger']
    guestname = params['guestname']
    vcpulist = params['vcpulist']
    state = params['state']

    if not utils.version_compare("libvirt-python", 3, 1, 0, logger):
        logger.info("Current libvirt-python don't support setVcpu().")
        return 0

    logger.info("guest name: %s" % guestname)
    logger.info("vcpulist: %s" % vcpulist)
    logger.info("state: %s" % state)

    if state == "enable":
        state_int = 1
    else:
        state_int = 0

    conn = sharedmod.libvirtobj['conn']

    try:
        domobj = conn.lookupByName(guestname)
        before = get_vcpu_number(domobj, logger)
        logger.info("start to set vcpu")
        domobj.setVcpu(vcpulist, state_int, 1)
        after = get_vcpu_number(domobj, logger)
    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    logger.info("check vcpu number")
    if state == "enable":
        if after[0] == before[0] + 1:
            logger.info("domain xml current vcpu is equal as set")
        else:
            logger.error("domain xml current vcpu is not equal as set")
            return 1
    else:
        if after[0] == before[0] - 1:
            logger.info("domain xml current vcpu is equal as set")
        else:
            logger.error("domain xml current vcpu is not equal as set")
            return 1

    username = utils.get_env('variables', 'username')
    passwd = utils.get_env('variables', 'password')
    mac = utils.get_dom_mac_addr(guestname)
    logger.debug("mac addr: %s" % mac)
    ip = utils.mac_to_ip(mac, 180)
    logger.debug("ip: %s" % ip)

    cmd = "cat /proc/cpuinfo | grep processor | wc -l"
    ret, output = utils.remote_exec_pexpect(ip, username, passwd, cmd)
    if not ret:
        logger.info("cpu number in domain is %s" % output)
        if int(output) == after[0]:
            logger.info("cpu in domain is equal to current vcpu value")
        else:
            logger.error("current vcpu is not equal as check in domain")
            return 1
    else:
        logger.error("get cpu number in guest failed.")
        return 1

    return 0
