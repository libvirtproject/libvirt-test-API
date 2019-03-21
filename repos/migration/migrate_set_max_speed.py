#!/usr/bin/env python
# Test migrateSetMaxSpeed()

import os
import time

import libvirt
from libvirt import libvirtError
from utils import utils

LOG_NAME = "/var/log/libvirt/libvirtd-test-api.log"

required_params = ('guestname', 'speed')
optional_params = {'flags': None}


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
    time.sleep(3)
    if ret:
        logger.error("restart libvirtd failed.")
        logger.error("out: %s" % out)
        return 1


def check_speed(dom, speed, logger):
    uuid = dom.UUIDString()
    cmd = ("grep 'virDomainMigrateSetMaxSpeed' %s | grep '%s' | grep '%s'" %
           (LOG_NAME, uuid, speed))
    ret, out = utils.exec_cmd(cmd, shell=True)
    logger.debug("cmd: %s" % cmd)
    if ret:
        logger.error("FAIL: set speed failed.")
        logger.error("out: %s" % out)
        return 1
    else:
        logger.info("PASS: set speed succefully.")

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
    time.sleep(3)
    if ret:
        logger.error("restart libvirtd failed.")
        logger.error("out: %s" % out)
        return 1

    if os.path.exists(LOG_NAME):
        os.remove(LOG_NAME)


def migrate_set_max_speed(params):
    """ migrate set max speed for a guest """
    logger = params['logger']
    guestname = params['guestname']
    speed = params['speed']
    test_result = False
    flags = params.get('speed_postcopy', None)

    if flags == "speed_postcopy":
        if not utils.version_compare("libvirt-python", 5, 0, 0, logger):
            logger.info("Current libvirt-python don't support flag VIR_DOMAIN_MIGRATE_MAX_SPEED_POSTCOPY.")
            return 0
        libvirt_flag = libvirt.VIR_DOMAIN_MIGRATE_MAX_SPEED_POSTCOPY
    else:
        libvirt_flag = 0

    logger.info("Set log config in libvirtd.conf.")
    if prepare_log_config(logger):
        return 1

    try:
        conn = libvirt.open()
        dom = conn.lookupByName(guestname)
        logger.info("Set max speed to %s" % speed)
        dom.migrateSetMaxSpeed(int(speed), libvirt_flag)
        if check_speed(dom, speed, logger):
            test_result = True
    except libvirtError as e:
        test_result = True
        logger.error("API error message: %s, error code: %s" %
                     (e.get_error_message(), e.get_error_code()))
    finally:
        clean_log_config(logger)
        if test_result:
            return 1
        else:
            return 0
