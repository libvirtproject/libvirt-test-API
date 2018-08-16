#!/usr/bin/env python
# Test domain vcpu pin with flag VIR_DOMAIN_AFFECT_CONFIG, check
# domain config xml with vcpupin configuration.

import libvirt

from xml.dom import minidom
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('guestname', 'vcpu', 'cpulist',)
optional_params = {}


def vcpupin_check(domobj, vcpu, cpumap):
    """check domain config xml with vcpupin element
    """
    guestxml = domobj.XMLDesc(2)
    logger.debug("domain %s xml :\n%s" % (domobj.name(), guestxml))

    doc = minidom.parseString(guestxml)
    vcpupin = doc.getElementsByTagName('vcpupin')
    if not vcpupin:
        logger.error("no vcpupin element in domain xml")
        return 1

    for i in range(len(vcpupin)):
        if vcpupin[i].hasAttribute('vcpu') and \
           vcpupin[i].hasAttribute('cpuset'):
            vcpu_attr = vcpupin[i].getAttributeNode('vcpu')
            cpu_attr = vcpupin[i].getAttributeNode('cpuset')
            if int(vcpu_attr.nodeValue) == vcpu:
                cpulist = cpu_attr.nodeValue
                if cpulist == '':
                    cpumap_tmp = ()
                    for i in range(maxcpu):
                        cpumap_tmp += (False,)
                else:
                    cpumap_tmp = utils.param_to_tuple(cpulist, maxcpu)

                if cpumap_tmp == cpumap:
                    logger.info("cpuset is as expected in domain xml")
                    return 0
                else:
                    logger.error("cpuset is not as expected in domain xml")
                    return 1

        if i == len(vcpupin) - 1:
            logger.error("the vcpupin element with given vcpu is not found")
            return 1


def vcpupin_config(params):
    """pin domain vcpu to host cpu with config flag
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
    conn = sharedmod.libvirtobj['conn']
    if utils.isPower():
        maxcpu = conn.getMaxVcpus('kvm')
    else:
        maxcpu = utils.get_host_cpus()
    logger.info("%s physical cpu on host" % maxcpu)

    try:
        domobj = conn.lookupByName(guestname)
        cpumap = utils.param_to_tuple(cpulist, maxcpu)

        if not cpumap:
            logger.error("cpulist: Invalid format")
            return 1

        logger.debug("cpumap for vcpu pin is:")
        logger.debug(cpumap)

        logger.info("pin domain vcpu %s to host cpulist %s with flag: %s" %
                    (vcpu, cpulist, libvirt.VIR_DOMAIN_AFFECT_CONFIG))
        domobj.pinVcpuFlags(vcpu, cpumap, libvirt.VIR_DOMAIN_AFFECT_CONFIG)

        logger.info("check vcpu pin info")
        ret = domobj.vcpuPinInfo(libvirt.VIR_DOMAIN_AFFECT_CONFIG)
        logger.debug("vcpu pin info is:")
        logger.debug(ret)
        if ret[vcpu] == cpumap:
            logger.info("vcpu pin info is expected")
        else:
            logger.error("vcpu pin info is not expected")
            return 1
    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    logger.info("check domain vcpupin configuration in xml")
    ret = vcpupin_check(domobj, vcpu, cpumap)
    if ret:
        logger.error("domain vcpu pin check failed")
        return 1
    else:
        logger.info("domain vcpu pin check succeed")
        return 0
