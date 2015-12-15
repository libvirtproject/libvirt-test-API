#!/usr/bin/env python
# Test set domain vcpu with flag VIR_DOMAIN_AFFECT_CONFIG or
# VIR_DOMAIN_VCPU_MAXIMUM, depend on which optional param is
# given.

from xml.dom import minidom

import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ('guestname', )
optional_params = {'vcpu': 1,
                   'maxvcpu': 8,
                   }


def get_vcpu_number(domobj):
    """dump domain config xml description to get vcpu number, return
       current vcpu and maximum vcpu number
    """
    try:
        guestxml = domobj.XMLDesc(2)
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


def set_vcpus_config(params):
    """set domain vcpu with config flag and check, also set and check
       max vcpu with maximum flag if optional param maxvcpu is given
    """
    global logger
    logger = params['logger']
    params.pop('logger')
    guestname = params['guestname']
    vcpu = params.get('vcpu', None)
    maxvcpu = params.get('maxvcpu', None)

    logger.info("the name of virtual machine is %s" % guestname)
    if vcpu is None and maxvcpu is None:
        logger.error("at least one of vcpu or maxvcpu should be provided")
        return 1

    conn = sharedmod.libvirtobj['conn']

    try:
        domobj = conn.lookupByName(guestname)
        if vcpu:
            flags = libvirt.VIR_DOMAIN_AFFECT_CONFIG
            logger.info("the given vcpu number is %s" % vcpu)
            logger.info("set domain vcpu as %s with flag: %s" %
                        (vcpu, flags))
            domobj.setVcpusFlags(int(vcpu), flags)
            logger.info("set domain vcpu succeed")

            logger.info("check with vcpusFlags api")
            ret = domobj.vcpusFlags(flags)
            logger.info("vcpusFlags return current vcpu is: %s" % ret)
            if ret == int(vcpu):
                logger.info("vcpusFlags check succeed")
            else:
                logger.error("vcpusFlags check failed")
                return 1

        if maxvcpu:
            flags = libvirt.VIR_DOMAIN_VCPU_MAXIMUM | libvirt.VIR_DOMAIN_AFFECT_CONFIG
            logger.info("the given max vcpu number is %s" % maxvcpu)
            logger.info("set domain maximum vcpu as %s with flag: %s" %
                        (maxvcpu, flags))
            domobj.setVcpusFlags(int(maxvcpu), flags)
            logger.info("set domain vcpu succeed")

            logger.info("check with vcpusFlags api")
            ret = domobj.vcpusFlags(flags)
            logger.info("vcpusFlags return max vcpu is: %s" % ret)
            if ret == int(maxvcpu):
                logger.info("vcpusFlags check succeed")
            else:
                logger.error("vcpusFlags check failed")
                return 1

    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    logger.info("check domain config xml to get vcpu number")
    ret = get_vcpu_number(domobj)
    if vcpu:
        if ret[0] == int(vcpu):
            logger.info("domain current vcpu is equal as set")
        else:
            logger.error("domain current vcpu is not equal as set")
            return 1

    if maxvcpu:
        if ret[1] == int(maxvcpu):
            logger.info("domain max vcpu is equal as set")
        else:
            logger.error("domain max vcpu is not equal as set")
            return 1

    return 0
