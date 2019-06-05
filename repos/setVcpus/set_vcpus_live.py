#!/usr/bin/env python
# Test set domain vcpu with flag VIR_DOMAIN_VCPU_LIVE. Check
# domain xml and inside domain to get current vcpu number. The
# live flag only work on running domain, so test on shutoff
# domain will fail.

import libvirt
import functools

from xml.dom import minidom
from libvirt import libvirtError
from src import sharedmod
from utils import utils

required_params = ('guestname', 'vcpu', 'username', 'password', )
optional_params = {}


def get_guest_vcpu(current, ip, username, password, logger):
    cmd = "cat /proc/cpuinfo | grep processor | wc -l"
    ret, output = utils.remote_exec_pexpect(ip, username, password, cmd)
    if not ret:
        logger.info("cpu number in domain is %s" % output)
        if int(output) == current:
            logger.info("cpu in domain is equal to current vcpu value")
            return True
        else:
            logger.error("current vcpu is not equal as check in domain")
            return False
    else:
        logger.error("check in domain fail: ret: %s, out: %s" % (ret, output))
        return False



def get_current_vcpu(domobj, username, password):
    """dump domain live xml description to get current vcpu number
       and check in domain to confirm
    """
    try:
        guestxml = domobj.XMLDesc(1)
        guestname = domobj.name()
        logger.debug("domain %s xml is :\n%s" % (guestname, guestxml))
        xml = minidom.parseString(guestxml)
        vcpu = xml.getElementsByTagName('vcpu')[0]

        if vcpu.hasAttribute('current'):
            attr = vcpu.getAttributeNode('current')
            current = int(attr.nodeValue)
        else:
            logger.info("no 'current' atrribute for element vcpu")
            current = int(vcpu.childNodes[0].data)

        logger.info("domain current vcpu number in live xml is: %s" % current)

    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return False

    mac = utils.get_dom_mac_addr(guestname)
    logger.info("mac address: %s" % mac)
    ip = utils.mac_to_ip(mac, 180)
    logger.info("guest ip: %s" % ip)
    logger.info("check cpu number in domain")
    ret = utils.wait_for(functools.partial(get_guest_vcpu, current, ip, username, password, logger), 180, step=5)
    if not ret:
        logger.error("get vcpu in guest timeout.")
        return False
    return current


def set_vcpus_live(params):
    """set domain vcpu with live flag and check
    """
    global logger
    logger = params['logger']
    params.pop('logger')
    guestname = params['guestname']
    vcpu = int(params['vcpu'])
    username = params['username']
    password = params['password']

    logger.info("the name of virtual machine is %s" % guestname)
    logger.info("the given vcpu number is %s" % vcpu)

    conn = sharedmod.libvirtobj['conn']

    try:
        domobj = conn.lookupByName(guestname)
        logger.info("set domain vcpu as %s with flag: %s" %
                    (vcpu, libvirt.VIR_DOMAIN_VCPU_LIVE))
        domobj.setVcpusFlags(vcpu, libvirt.VIR_DOMAIN_VCPU_LIVE)
        logger.info("check with vcpusFlags api")
        ret = domobj.vcpusFlags(libvirt.VIR_DOMAIN_VCPU_LIVE)
        logger.info("vcpusFlags return current vcpu is: %s" % ret)
        if ret == vcpu:
            logger.info("vcpusFlags check succeed")
        else:
            logger.error("vcpusFlags check failed")
            return 1
    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    logger.info("check domain vcpu")
    ret = get_current_vcpu(domobj, username, password)
    if ret == vcpu:
        logger.info("domain vcpu is equal as set")
        return 0
    else:
        logger.error("domain vcpu is not equal as set")
        return 1
