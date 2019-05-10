#!/usr/bin/env python
# Test setVcpusFlags()

import lxml
import lxml.etree
import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('guestname', 'vcpu', 'flags')
optional_params = {}


def check_result(dom, flags, vcpu, logger):
    username = utils.get_env('variables', 'username')
    passwd = utils.get_env('variables', 'password')

    guestname = dom.name()
    mac = utils.get_dom_mac_addr(guestname)
    logger.debug("mac addr: %s" % mac)
    ip = utils.mac_to_ip(mac, 180)
    logger.debug("ip: %s" % ip)

    if '|' not in flags:
        logger.info("unexpected flags: %s" % flags)
        return 1
    else:
        if 'live' in flags and 'hotpluggable' in flags:
            if not utils.version_compare("libvirt-python", 2, 5, 0, logger):
                logger.info("Current libvirt-python don't support 'hotpluggable' flag.")
                return 0

            cmd = "cat /proc/cpuinfo | grep processor | wc -l"
            ret, out = utils.remote_exec_pexpect(ip, username, passwd, cmd)
            if ret:
                logger.error("From guest to get cpu number failed.")
                logger.error("ret: %s, out: %s" % (ret, out))
                return 1
            if int(out) == vcpu:
                logger.info("cpu in domain is equal to current vcpu value")
            else:
                logger.error("current vcpu is not equal as check in domain")
                return 1

            if dom.isActive() == 1:
                tree = lxml.etree.fromstring(dom.XMLDesc(0))
            else:
                tree = lxml.etree.fromstring(dom.XMLDesc(libvirt.VIR_DOMAIN_XML_INACTIVE))

            vcpu_list = tree.xpath("/domain/vcpus/vcpu")
            num = 0
            for i in vcpu_list:
                state = i.attrib['enabled']
                if state == "yes":
                    num = num + 1

            if num != vcpu:
                logger.error("For hotpluggable flag, vcpu number is not equal as check in xml.")
                return 1

    return 0


def get_flag(flag, logger):
    ret = 0
    if flag == "live":
        ret = ret | libvirt.VIR_DOMAIN_VCPU_LIVE
    elif flag == "config":
        ret = ret | libvirt.VIR_DOMAIN_VCPU_CONFIG
    elif flag == "current":
        ret = ret | libvirt.VIR_DOMAIN_VCPU_CURRENT
    elif flag == "guest":
        ret = ret | libvirt.VIR_DOMAIN_VCPU_GUEST
    elif flag == "maximum":
        ret = ret | libvirt.VIR_DOMAIN_VCPU_MAXIMUM
    elif flag == "hotpluggable":
        if utils.version_compare("libvirt-python", 2, 5, 0, logger):
            ret = ret | libvirt.VIR_DOMAIN_VCPU_HOTPLUGGABLE
    else:
        logger.error("Don't support flag %s." % flag)

    return ret


def parse_flags(flags, logger):
    if '|' not in flags:
        return get_flag(flags, logger)
    else:
        flags_list = flags.split('|')
        for i in flags_list:
            return get_flag(i, logger)


def set_vcpus_flags(params):
    """set domain vcpu with flags
    """
    logger = params['logger']
    guestname = params['guestname']
    vcpu = int(params['vcpu'])
    flags = params['flags']

    if utils.check_qemu_package("qemu-kvm") and not utils.version_compare("qemu-kvm", 2, 12, 0, logger):
        logger.info("Current qemu-kvm don't support this API.")
        return 0

    logger.info("guestname: %s" % guestname)
    logger.info("vcpu number: %s" % vcpu)
    logger.info("flags: %s" % flags)

    libvirt_flags = parse_flags(flags, logger)

    conn = sharedmod.libvirtobj['conn']
    try:
        dom = conn.lookupByName(guestname)
        dom.setVcpusFlags(vcpu, libvirt_flags)
    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    if check_result(dom, flags, vcpu, logger):
        logger.error("FAIL: set guest vcpus with flags failed.")
        return 1
    else:
        logger.info("PASS: set guest vcpus with flags successful.")

    return 0
