#!/usr/bin/env python

import threading
import time
import libvirt
import json

from libvirt import libvirtError
from repos.domain import domain_common
from utils import utils
from utils import process

required_params = ('target_machine',
                   'username',
                   'password',
                   'guestname',)
optional_params = {'params_list': None}

test_result = True


def clean_guest(conn, guestname, logger):
    running_guests = []
    ids = conn.listDomainsID()
    for id in ids:
        obj = conn.lookupByID(id)
        running_guests.append(obj.name())

    if guestname in running_guests:
        logger.info("Destroy guest: %s" % guestname)
        domobj = conn.lookupByName(guestname)
        domobj.destroy()

    define_guests = conn.listDefinedDomains()
    if guestname in define_guests:
        logger.info("Undefine guest: %s" % guestname)
        domobj = conn.lookupByName(guestname)
        domobj.undefine()


def env_clean(srcc, dstc, guestname, logger):
    logger.info("destroy and undefine %s on both side if it exsits", guestname)
    clean_guest(srcc, guestname, logger)
    clean_guest(dstc, guestname, logger)


def migrate(srcc, srcd, dstc, guestname, params_list, logger):
    global test_result
    try:
        srcd.migrateSetMaxSpeed(1, 0)
        speed = srcd.migrateGetMaxSpeed(0)
        logger.info("Set migrate max speed to %s." % speed)
        if params_list is not None:
            flags = libvirt.VIR_MIGRATE_LIVE | libvirt.VIR_MIGRATE_PARALLEL
            logger.info("Use migrate3() to migrate.")
            srcd.migrate3(dstc, json.loads(params_list), flags)
        else:
            flags = libvirt.VIR_MIGRATE_LIVE | libvirt.VIR_MIGRATE_PEER2PEER | libvirt.VIR_MIGRATE_PARALLEL
            logger.info("use migrate() to migrate")
            srcd.migrate(dstc, flags, None, None, 0)
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        test_result = False
        env_clean(srcc, dstc, guestname, logger)
        return 1

    return 0


def check_conn(params_list, logger):
    global test_result
    logger.info("Start check network connections.")
    cmd = "timeout 5 netstat -tunapc | grep 4915 | grep ESTABLISHED | awk '{print $4}' | awk -F: '{print $2}' | sort | uniq"
    ret = process.run(cmd, shell=True, ignore_status=True)
    logger.info("out: %s" % ret.stdout)
    if ret.exit_status:
        logger.error("%s failed." % ret.stdout)
        test_result = False
        return 1
    out_conn = len(ret.stdout.split('\n'))
    logger.info("Get connections number: %s" % out_conn)
    if params_list is None:
        if out_conn != 3:
            logger.error("Get network connections number error.")
            test_result = False
            return 1
    else:
        parallel_conn = json.loads(params_list)
        if out_conn != (parallel_conn['parallel.connections'] + 1):
            logger.error("Get network connections number error.")
            test_result = False
            return 1
    return 0


def migrate_parallel(params):
    """ Test migrate with parallel and parallel-connections flag """
    global test_result
    logger = params['logger']
    target_machine = params['target_machine']
    username = params['username']
    password = params['password']
    guestname = params['guestname']
    params_list = params.get('params_list', None)

    logger.info('Params list: %s' % params_list)
    if not utils.version_compare('libvirt-python', 5, 6, 0, logger):
        logger.info("Current libvirt-python don't support --parallel/--parallel-connections.")
        conn = libvirt.open()
        clean_guest(conn, guestname, logger)
        return 0

    domain_common.config_ssh(target_machine, username, password, logger)
    dsturi = "qemu+ssh://%s/system" % target_machine
    dstc = libvirt.open(dsturi)

    # Connect to local hypervisor connection URI
    srcc = libvirt.open()
    srcd = srcc.lookupByName(guestname)

    try:
        m = threading.Thread(target=migrate, args=(srcc, srcd, dstc, guestname, params_list, logger))
        p = threading.Thread(target=check_conn, args=(params_list, logger))

        m.start()
        time.sleep(3)
        p.start()

        m.join()
        p.join()

        if srcd.isActive():
            test_result = False
            logger.error("Source VM is still active")

        if not srcd.isPersistent():
            test_result = False
            logger.error("Source VM missing config")

        dstdom = dstc.lookupByName(guestname)
        if not dstdom.isActive():
            test_result = False
            logger.error("Dst VM is not active")

        if dstdom.info()[0] != libvirt.VIR_DOMAIN_RUNNING:
            test_result = False
            logger.error("Dst VM wrong state %s, should be running", dstdom.info()[0])

    except libvirtError as e:
        test_result = False
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("Migration Failed")
    finally:
        env_clean(srcc, dstc, guestname, logger)
        if not test_result:
            return 1
        else:
            logger.info("Migration PASS")
            return 0
