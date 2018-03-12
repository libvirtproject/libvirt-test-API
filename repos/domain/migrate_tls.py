#!/usr/bin/env python

import libvirt

from libvirt import libvirtError
from src import sharedmod
from repos.domain import domain_common
from utils import utils, process

required_params = ('transport',
                   'target_machine',
                   'username',
                   'password',
                   'guestname',
                   'poststate')
optional_params = {}


def get_state(state):
    dom_state = ''
    if state == libvirt.VIR_DOMAIN_NOSTATE:
        dom_state = 'nostate'
    elif state == libvirt.VIR_DOMAIN_RUNNING:
        dom_state = 'running'
    elif state == libvirt.VIR_DOMAIN_BLOCKED:
        dom_state = 'blocked'
    elif state == libvirt.VIR_DOMAIN_PAUSED:
        dom_state = 'paused'
    elif state == libvirt.VIR_DOMAIN_SHUTDOWN:
        dom_state = 'shutdown'
    elif state == libvirt.VIR_DOMAIN_SHUTOFF:
        dom_state = 'shutoff'
    elif state == libvirt.VIR_DOMAIN_CRASHED:
        dom_state = 'crashed'
    else:
        dom_state = 'no sure'
    return dom_state


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


def env_clean(srcconn, dstconn, guestname, logger):
    logger.info("destroy and undefine %s on both side if it exsits", guestname)
    clean_guest(srcconn, guestname, logger)
    clean_guest(dstconn, guestname, logger)


def migrate_tls(params):
    """ migrate a guest back and forth between two machines"""
    logger = params['logger']

    transport = params['transport']
    target_machine = params['target_machine']
    username = params['username']
    password = params['password']
    guestname = params['guestname']
    poststate = params['poststate']

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

    ret = process.run("ssh-add", shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("ssh-add failed: %s" % ret.stdout)
        return 1
    target_hostname = utils.get_target_hostname(target_machine, username, password, logger)
    dsturi = "qemu+%s://%s/system" % (transport, target_hostname)

    # Connect to local hypervisor connection URI
    srcconn = sharedmod.libvirtobj['conn']
    srcdom = srcconn.lookupByName(guestname)
    dstconn = libvirt.open(dsturi)

    try:
        logger.info("use migrate() to migrate")
        srcdom.migrate(dstconn, libvirt.VIR_MIGRATE_TLS, None, None, 0)
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        logger.error("Migration Failed")
        env_clean(srcconn, dstconn, guestname, logger)
        return 1

    dstdom = dstconn.lookupByName(guestname)
    dstdom_state = dstdom.info()[0]
    if get_state(dstdom_state) != poststate:
        logger.error("Dst VM wrong state %s, should be %s", get_state(dstdom_state), poststate)
        env_clean(srcconn, dstconn, guestname, logger)
        return 1

    logger.info("Migration PASS")
    env_clean(srcconn, dstconn, guestname, logger)
    return 0
