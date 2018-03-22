#!/usr/bin/env python
# To test abortJob API

import threading
import os

from libvirt import libvirtError
from src import sharedmod

required_params = ('guestname',)
optional_params = {}

DUMP_PATH = "/tmp/test-api-abortjob.dump"


def domain_dump(dom, logger):
    logger.info("start to dump job.")
    try:
        dom.coreDump(DUMP_PATH, 0)
    except libvirtError as e:
        logger.error("info: %s, code: %s" % (e.get_error_message(), e.get_error_code()))

    return


def start_abort_job(dom, logger):
    logger.info("start to abort job.")
    try:
        dom.abortJob()
    except libvirtError as e:
        logger.error("info: %s, code: %s" % (e.get_error_message(), e.get_error_code()))

    return


def abort_job(params):
    logger = params['logger']
    guestname = params.get('guestname')

    logger.info("guestname: %s" % guestname)
    if os.path.exists(DUMP_PATH):
        os.remove(DUMP_PATH)

    try:
        conn = sharedmod.libvirtobj['conn']
        domobj = conn.lookupByName(guestname)
        d = threading.Thread(target=domain_dump, args=(domobj, logger))
        s = threading.Thread(target=start_abort_job, args=(domobj, logger))

        d.start()
        s.start()
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    d.join()
    s.join()

    if os.path.exists(DUMP_PATH):
        logger.error("Fail: abort dump job failed. dump file exist.")
    else:
        logger.info("Pass: abortdump job successful.")

    return 0
