#!/usr/bin/env python

import threading
import time
import json

import libvirt
from libvirt import libvirtError
from repos.domain import domain_common

required_params = ('target_machine',
                   'username',
                   'password',
                   'guestname',
                   'flags')
optional_params = {'params_list': None}


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


def migrate_postcopy(srcc, srcd, dstc, guestname, params_list, flags, logger):
    try:
        logger.info("start use migrate3() to migrate")
        srcd.migrate3(dstc, params_list, flags)
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        env_clean(srcc, dstc, guestname, logger)
        return 1

    return 0


def postcopy_bandwidth(srcc, srcd, dstc, guestname, params_list, logger):
    try:
        logger.info("get postcopy bandwidth.")
        speed = srcd.migrateGetMaxSpeed(libvirt.VIR_DOMAIN_MIGRATE_MAX_SPEED_POSTCOPY)
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        env_clean(srcc, dstc, guestname, logger)
        return 1

    logger.info("speed: %s" % speed)
    if speed == params_list['bandwidth.postcopy']:
        logger.info("migrate with postcopy-bandwidth successed.")
        return 0
    else:
        logger.error("migrate with postcopy-bandwidth failed.")
        env_clean(srcc, dstc, guestname, logger)
        return 1


def migrate3(params):
    """ using migrate3() to migration """
    logger = params['logger']
    target_machine = params['target_machine']
    username = params['username']
    password = params['password']
    guestname = params['guestname']
    flags = params['flags']
    test_result = False

    tmp_list = params.get('params_list', None)
    params_list = None
    if tmp_list:
        params_list = json.loads(tmp_list)

    logger.info("the flags is %s" % flags)
    flags_string = flags.split("|")

    migflags = 0
    for flag in flags_string:
        if flag == '0':
            migflags |= 0
        elif flag == 'peer2peer':
            migflags |= libvirt.VIR_MIGRATE_PEER2PEER
        elif flag == 'tunnelled':
            migflags |= libvirt.VIR_MIGRATE_TUNNELLED
        elif flag == 'live':
            migflags |= libvirt.VIR_MIGRATE_LIVE
        elif flag == 'persist_dest':
            migflags |= libvirt.VIR_MIGRATE_PERSIST_DEST
        elif flag == 'undefine_source':
            migflags |= libvirt.VIR_MIGRATE_UNDEFINE_SOURCE
        elif flag == 'paused':
            migflags |= libvirt.VIR_MIGRATE_PAUSED
        elif flag == 'postcopy':
            migflags |= libvirt.VIR_MIGRATE_POSTCOPY
        elif flag == 'unsafe':
            migflags |= libvirt.VIR_MIGRATE_UNSAFE
        else:
            logger.error("unknown flag")
            return 1

    domain_common.config_ssh(target_machine, username, password, logger)

    try:
        dsturi = "qemu+ssh://%s/system" % target_machine
        dstc = libvirt.open(dsturi)

        # Connect to local hypervisor connection URI
        srcc = libvirt.open()
        srcd = srcc.lookupByName(guestname)

        if "postcopy" in flags:
            m = threading.Thread(target=migrate_postcopy, args=(srcc, srcd, dstc, guestname, params_list, migflags, logger))
            p = threading.Thread(target=postcopy_bandwidth, args=(srcc, srcd, dstc, guestname, params_list, logger))

            m.start()
            time.sleep(1)
            p.start()

            m.join()
            p.join()
        else:
            srcd.migrate3(dstc, migflags, None)

        if srcd.isActive():
            test_result = True
            logger.error("Source VM is still active")

        if not srcd.isPersistent():
            test_result = True
            logger.error("Source VM missing config")

        dstdom = dstc.lookupByName(guestname)
        if not dstdom.isActive():
            test_result = True
            logger.error("Dst VM is not active")

        if dstdom.info()[0] != libvirt.VIR_DOMAIN_RUNNING:
            test_result = True
            logger.error("Dst VM wrong state %s, should be running", dstdom.info()[0])

    except libvirtError as e:
        test_result = True
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("Migration Failed")
    finally:
        env_clean(srcc, dstc, guestname, logger)
        if test_result:
            return 1
        else:
            logger.info("Migration PASS")
            return 0
