#!/usr/bin/env python
# Test migrateGetMaxDowntime()

import json
import libvirt
import libvirt_qemu
from libvirt import libvirtError

required_params = ('guestname',)
optional_params = {}


def get_downtime_from_qemu(dom, logger):
    ret = libvirt_qemu.qemuMonitorCommand(dom, '{ "execute": "query-migrate-parameters" }', 0)
    out = json.loads(ret)

    if "downtime-limit" in out["return"].keys():
        return out['return']['downtime-limit']
    else:
        logger.error("cannot find downtime-limit in query-migrate-parameters.")
        return None


def migrate_get_max_downtime(params):
    """ migrate get max downtime for a guest """
    logger = params['logger']
    guestname = params['guestname']

    if not utils.version_compare("libvirt-python", 3, 7, 0, logger):
        logger.info("Current libvirt-python don't support migrateGetMaxDowntime().")
        return 0

    try:
        conn = libvirt.open()
        dom = conn.lookupByName(guestname)
        downtime_limit = get_downtime_from_qemu(dom, logger)
        logger.info("get downtime from query-migrate-parameters: %s" % downtime_limit)

        downtime = dom.migrateGetMaxDowntime(0)
        logger.info("get downtime from migrateGetMaxDowntime: %s" % downtime)
    except libvirtError, e:
        logger.error("API error message: %s, error code: %s" %
                     (e.message, e.get_error_code()))
        return 1

    if downtime == downtime_limit:
        logger.info("PASS: get max downtime successful.")
        return 0
    else:
        logger.info("FAIL: get max downtime failed.")
        return 1
