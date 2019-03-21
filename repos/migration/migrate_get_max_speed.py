#!/usr/bin/env python
# Test migrateGetMaxSpeed()

import json
import libvirt
import libvirt_qemu

from libvirt import libvirtError
from utils import utils

required_params = ('guestname',)
optional_params = {'flags': None}


def get_speed_from_qemu(dom, flags, logger):
    ret = libvirt_qemu.qemuMonitorCommand(dom, '{ "execute": "query-migrate-parameters" }', 0)
    out = json.loads(ret)

    if flags == "speed_postcopy":
        if "max-postcopy-bandwidth" in list(out["return"].keys()):
            return out['return']['max-postcopy-bandwidth']
        else:
            logger.error("cannot find max-postcopy-bandwidth in query-migrate-parameters.")
            return None
    else:
        if "max-bandwidth" in list(out["return"].keys()):
            return out['return']['max-bandwidth']
        else:
            logger.error("cannot find max-bandwidth in query-migrate-parameters.")
            return None


def migrate_get_max_speed(params):
    """ migrate get max speed for a guest """
    logger = params['logger']
    guestname = params['guestname']
    flags = params.get('flags', None)

    if flags == "speed_postcopy":
        if not utils.version_compare("libvirt-python", 5, 0, 0, logger):
            logger.info("Current libvirt-python don't support flag VIR_DOMAIN_MIGRATE_MAX_SPEED_POSTCOPY.")
            return 0
        libvirt_flag = libvirt.VIR_DOMAIN_MIGRATE_MAX_SPEED_POSTCOPY
    else:
        libvirt_flag = 0

    try:
        conn = libvirt.open()
        dom = conn.lookupByName(guestname)
        speed_limit = get_speed_from_qemu(dom, flags, logger)
        logger.info("get speed from query-migrate-parameters: %s" % speed_limit)

        speed = dom.migrateGetMaxSpeed(libvirt_flag)
        logger.info("get speed from migrateGetMaxSpeed: %s" % speed)
    except libvirtError as e:
        logger.error("API error message: %s, error code: %s" %
                     (e.get_error_message(), e.get_error_code()))
        return 1

    if flags != "speed_postcopy":
        # The default maximum migration speed of 8796093022207 MiB/s is
        # INT64_MAX / (1024 * 1024), where INT64_MAX is the maximum value
        # QEMU supports and we need to divide it by 1024 * 1024 because
        # QEMU takes B/s while we use MiB/s.
        if speed == 8796093022207:
            logger.info("PASS: get max speed successful.")
            return 0
        else:
            speed = speed * 1024 * 1024
    if speed == speed_limit:
        logger.info("PASS: get max speed successful.")
        return 0
    else:
        logger.info("FAIL: get max speed failed.")
        return 1
