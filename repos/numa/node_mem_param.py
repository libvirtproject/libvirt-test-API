#!/usr/bin/env python
# Test tuning host node memory parameters

import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ()
optional_params = {"shm_pages_to_scan": 100,
                   "shm_sleep_millisecs": 20,
                   "shm_merge_across_nodes": 1
                  }

KSM_PATH = "/sys/kernel/mm/ksm/"

def node_mem_param(params):
    """test set host node memory parameters
    """
    logger = params['logger']
    shm_pages_to_scan = params.get('shm_pages_to_scan')
    shm_sleep_millisecs = params.get('shm_sleep_millisecs')
    shm_merge_across_nodes = params.get('shm_merge_across_nodes')

    if not shm_pages_to_scan \
        and not shm_sleep_millisecs \
        and not shm_merge_across_nodes:
        logger.error("given param is none")
        return 1

    param_dict = {}
    for i in optional_params.keys():
        if eval(i):
            param_dict[i] = int(eval(i))

    logger.info("the given param dict is: %s" % param_dict)

    conn = sharedmod.libvirtobj['conn']

    try:
        logger.info("get host node memory parameters")
        mem_pre = conn.getMemoryParameters(0)
        logger.info("host node memory parameters is: %s" % mem_pre)

        logger.info("set host node memory parameters with given param %s" %
                    param_dict)
        conn.setMemoryParameters(param_dict, 0)
        logger.info("set host node memory parameters done")

        logger.info("get host node memory parameters")
        mem_pos = conn.getMemoryParameters(0)
        logger.info("host node memory parameters is: %s" % mem_pos)

        for i in param_dict.keys():
            if not mem_pos[i] == param_dict[i]:
                logger.error("%s is not set as expected" % i)

        logger.info("node memory parameters is set as expected")

        logger.info("check tuning detail under %s" % KSM_PATH)

        ksm_dict = {}
        for i in param_dict.keys():
            path = "%s%s" % (KSM_PATH, i[4:])
            f = open(path)
            ret = int(f.read().split('\n')[0])
            f.close()
            logger.info("%s value is: %s" % (path, ret))
            ksm_dict[i] = ret

        if ksm_dict == param_dict:
            logger.info("tuning detail under %s is expected" % KSM_PATH)
        else:
            logger.error("check with tuning detail under %s failed"  % KSM_PATH)
            return 1

    except libvirtError, e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    return 0
