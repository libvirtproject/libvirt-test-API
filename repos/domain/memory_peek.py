#!/usr/bin/env python
# Test domain memory peek

import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ('guestname', )
optional_params = {'page_offset':''}


def memory_peek(params):
    """domain memory peek
    """
    logger = params['logger']
    guestname = params['guestname']
    #If page_offset not given, use Linux default page_offset for x86
    page_offset = int(params.get('page_offset', 0xffff880000000000), 0)

    flag_dict = {1: "VIR_MEMORY_VIRTUAL", 2: "VIR_MEMORY_PHYSICAL"}
    addr_dict = {1: page_offset,
                 2: 0x0000000000000000}

    logger.info("the name of virtual machine is %s" % guestname)

    conn = sharedmod.libvirtobj['conn']

    try:
        domobj = conn.lookupByName(guestname)
        logger.info("test memory peek API")
        for flag in list(flag_dict.keys()):
            logger.info("using flag: %s" % flag_dict[flag])
            mem = domobj.memoryPeek(addr_dict[flag], 0, flag)
            if mem:
                return 1
            logger.info("memory peek API works fine with flag: %s" %
                        flag_dict[flag])

        logger.info("peek 8 bytes from domain memory")
        for flag in list(flag_dict.keys()):
            logger.info("using flag: %s" % flag_dict[flag])
            mem = domobj.memoryPeek(addr_dict[flag], 8, flag)
            if not mem:
                return 1
            logger.info("8 bytes start with 0 with flag %s is: %s" %
                        (flag_dict[flag], mem))

    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        # Return true if we provide an invalid address
        if "Invalid addr" in str(e):
            return 0
        return 1

    return 0
