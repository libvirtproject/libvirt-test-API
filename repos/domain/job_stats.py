#!/usr/bin/env python

import os

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils.utils import parse_flags, version_compare

required_params = ('guestname',)
optional_params = {'flags': None}

DUMP_PATH = "/tmp/test-api-job-stats.dump"


def job_stats(params):
    """Test get job stats
    """
    guestname = params['guestname']
    flags = parse_flags(params, param_name='flags')
    logger = params['logger']
    logger.info("guestname: %s" % guestname)
    logger.info("flags: %s" % flags)

    try:
        conn = sharedmod.libvirtobj['conn']
        domobj = conn.lookupByName(guestname)
        if flags == libvirt.VIR_DOMAIN_JOB_STATS_COMPLETED:
            logger.info("start dump guest to %s:" % DUMP_PATH)
            domobj.coreDump(DUMP_PATH, 0)
        info = domobj.jobStats(flags)
        logger.info("job stats: %s" % info)
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    if flags == libvirt.VIR_DOMAIN_JOB_STATS_COMPLETED:
        if version_compare("libvirt", 2, 5, 0, logger):
            if info['operation'] == 8:
                logger.info("PASS: get job stats ok.")
            else:
                logger.error("FAIL: get job stats failed.")
        else:
            if info['type'] == 3:
                logger.info("PASS: get job stats ok.")
            else:
                logger.error("FAIL: get job stats failed.")
    else:
        if info['type'] == 0:
            logger.info("PASS: get job stats ok.")
        else:
            logger.error("FAIL: get job stats failed.")

    return 0


def job_stats_clean(params):
    if os.path.exists(DUMP_PATH):
        os.remove(DUMP_PATH)
