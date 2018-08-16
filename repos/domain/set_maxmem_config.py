#!/usr/bin/env python
# Test set domain max memory with API setMaxMemory.

from xml.dom import minidom
from libvirt import libvirtError

from src import sharedmod

required_params = ('guestname', 'memory', )
optional_params = {}


def set_maxmem_config(params):
    """set domain max memory, check with config xml and
       maxMemory API
    """
    global logger
    logger = params['logger']
    guestname = params['guestname']
    memory = int(params['memory'])

    logger.info("the name of virtual machine is %s" % guestname)
    logger.info("the given max memory value is %s" % memory)

    conn = sharedmod.libvirtobj['conn']

    try:
        domobj = conn.lookupByName(guestname)
        logger.info("set domain max memory as %s" % memory)
        domobj.setMaxMemory(memory)

        guestxml = domobj.XMLDesc(2)
        logger.debug("domain %s xml is :\n%s" % (guestname, guestxml))
        xml = minidom.parseString(guestxml)
        mem = xml.getElementsByTagName('memory')[0]
        maxmem = int(mem.childNodes[0].data)
        logger.info("domain max memory in config xml is: %s" % maxmem)
        if maxmem == memory:
            logger.info("max memory in domain config xml is equal to set")
        else:
            logger.error("set max memory failed")
            return 1

        maxmem = domobj.maxMemory()
        logger.info("max memory got by maxMemory API is: %s" % maxmem)
        if maxmem == memory:
            logger.info("max memory got by maxMemory API is equal to set")
        else:
            logger.error("set max memory failed")
            return 1

        logger.info("set max memory succeed")

    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    return 0
