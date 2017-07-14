#!/usr/bin/env python

import commands
import threading
import time

import libvirt
from libvirt import libvirtError
from repos.domain import domain_common

required_params = ('target_machine',
                   'username',
                   'password',
                   'guestname',)
optional_params = {}


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


def migrate(srcc, srcd, dstc, guestname, logger):
    try:
        flags = libvirt.VIR_MIGRATE_LIVE | libvirt.VIR_MIGRATE_POSTCOPY
        logger.info("use migrate() to migrate")
        srcd.migrate(dstc, flags, None, None, 0)
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        env_clean(srcc, dstc, guestname, logger)
        return 1

    return 0


def postcopy(srcc, srcd, dstc, guestname, logger):
    try:
        logger.info("start postcopy migration.")
        srcd.migrateStartPostCopy(0)
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        env_clean(srcc, dstc, guestname, logger)
        return 1

    return 0


def migrate_postcopy(params):
    """ switch to post-copu using the migrate-postcopy """
    logger = params['logger']
    target_machine = params['target_machine']
    username = params['username']
    password = params['password']
    guestname = params['guestname']
    test_result = False

    #generate ssh key pair
    ret = domain_common.ssh_keygen(logger)
    if ret:
        logger.error("failed to generate RSA key")
        return 1
    #setup ssh tunnel with target machine
    ret = domain_common.ssh_tunnel(target_machine, username, password, logger)
    if ret:
        logger.error("faild to setup ssh tunnel with target machine %s" % target_machine)
        return 1

    commands.getstatusoutput("ssh-add")

    dsturi = "qemu+ssh://%s/system" % target_machine
    dstc = libvirt.open(dsturi)

    # Connect to local hypervisor connection URI
    srcc = libvirt.open()
    srcd = srcc.lookupByName(guestname)

    try:
        m = threading.Thread(target=migrate, args=(srcc, srcd, dstc, guestname, logger))
        p = threading.Thread(target=postcopy, args=(srcc, srcd, dstc, guestname, logger))

        m.start()
        time.sleep(1)
        p.start()

        m.join()
        p.join()

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

    except libvirtError, e:
        test_result = True
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        logger.error("Migration Failed")
    finally:
        env_clean(srcc, dstc, guestname, logger)
        if test_result:
            return 1
        else:
            logger.info("Migration PASS")
            return 0
