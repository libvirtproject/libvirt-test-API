#!/usr/bin/env python
# Test migrateSetMaxDowntime()

import os

import libvirt
from libvirt import libvirtError
from utils import utils

LOG_NAME = "/var/log/libvirt/libvirtd-test-api.log"

required_params = ('guestname', 'downtime', )
optional_params = {}


def prepare_log_config(logger):
    cmd = "echo 'log_level = 1' >> /etc/libvirt/libvirtd.conf"
    ret, out = utils.exec_cmd(cmd, shell=True)
    logger.debug("cmd: %s" % cmd)
    if ret:
        logger.error("set env for log failed.")
        logger.error("out: %s" % out)
        return 1

    cmd = "echo 'log_outputs=\"1:file:%s\"' >> /etc/libvirt/libvirtd.conf" % LOG_NAME
    ret, out = utils.exec_cmd(cmd, shell=True)
    logger.debug("cmd: %s" % cmd)
    if ret:
        logger.error("set env for log failed.")
        logger.error("out: %s" % out)
        return 1

    cmd = "service libvirtd restart"
    ret, out = utils.exec_cmd(cmd, shell=True)
    logger.debug("cmd: %s" % cmd)
    if ret:
        logger.error("restart libvirtd failed.")
        logger.error("out: %s" % out)
        return 1


def check_downtime(dom, downtime, logger):
    uuid = dom.UUIDString()
    cmd = ("grep 'virDomainMigrateSetMaxDowntime' %s | grep '%s' | grep '%s'" %
           (LOG_NAME, uuid, downtime))
    ret, out = utils.exec_cmd(cmd, shell=True)
    logger.debug("cmd: %s" % cmd)
    if ret:
        logger.error("FAIL: set downtime failed.")
        logger.error("out: %s" % out)
        return 1
    else:
        logger.info("PASS: set downtime succefully.")

    return 0


def clean_log_config(logger):
    logger.info("Clean log config in libvirtd.conf.")
    cmd = "sed -i -n \"/^[ #]/p\" /etc/libvirt/libvirtd.conf"
    ret, out = utils.exec_cmd(cmd, shell=True)
    logger.debug("cmd: %s" % cmd)
    if ret:
        logger.error("clean env for log failed.")
        logger.error("out: %s" % out)
        return 1

    cmd = "service libvirtd restart"
    ret, out = utils.exec_cmd(cmd, shell=True)
    logger.debug("cmd: %s" % cmd)
    if ret:
        logger.error("restart libvirtd failed.")
        logger.error("out: %s" % out)
        return 1

    if os.path.exists(LOG_NAME):
        os.remove(LOG_NAME)


def migrate_set_max_downtime(params):
    """ migrate set max downtime for a guest """
    logger = params['logger']
    guestname = params['guestname']
    downtime = params['downtime']
    test_result = False

    logger.info("Set log config in libvirtd.conf.")
    if prepare_log_config(logger):
        return 1

    try:
        conn = libvirt.open()
        dom = conn.lookupByName(guestname)
        logger.info("Set max downtime to %s" % downtime)
        dom.migrateSetMaxDowntime(int(downtime), 0)
        if check_downtime(dom, downtime, logger):
            test_result = True
    except libvirtError, e:
        test_result = True
        logger.error("API error message: %s, error code: %s" %
                     (e.message, e.get_error_code()))
    finally:
        clean_log_config(logger)
        if test_result:
            return 1
        else:
            return 0
