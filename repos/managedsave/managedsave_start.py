#!/usr/bin/env python

import time

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('guestname',)
optional_params = {'flags': ''}

NONE = 0
START_PAUSED = 1


def check_savefile_remove(*args):
    """Check guest managed save file"""
    (guestname) = args
    cmds = "ls /var/lib/libvirt/qemu/save/%s" % guestname + ".save -lh"
    logger.info("Execute cmd  %s" % cmds)
    (status, output) = utils.exec_cmd(cmds, shell=True)
    if status != 0:
        logger.info("No managed save file")
        return True
    else:
        logger.error("managed save file exists")
        return False


def managedsave_start(params):
    """ Start domain with managedsave image and check if its status is right
        according to given flags of running managedsave command.If it is
        correctly paused , resume it.

        Argument is a dictionary with two keys:
        {'logger': logger, 'guestname': guestname}

        logger -- an object of utils/log.py
        mandatory arguments : guestname -- same as the domain name
        optional arguments : flags -- domain create flags <none|start_paused
        |noping>.It allows only one flag be given.

        Return 0 on SUCCESS or 1 on FAILURE
    """
    domname = params['guestname']
    global logger
    logger = params['logger']
    flags = params.get('flags', '')
    # Get given flags of managedsave
    if 'flagsave' in sharedmod.data:
        flagsave = sharedmod.data.get('flagsave')
    else:
        logger.error("Failed to get flags from managedsave")
    # Clean sharedmod.data
    sharedmod.data = {}

    conn = sharedmod.libvirtobj['conn']
    domobj = conn.lookupByName(domname)

    timeout = 600
    logger.info('start domain')
    # Check if guest has managedsave image before start
    if domobj.hasManagedSaveImage(0):
        logger.info("Domain has managedsave image")
    else:
        logger.info("Domain hasn't managedsave image")

    try:
        if "none" in flags:
            domobj.createWithFlags(NONE)
        elif "start_paused" in flags:
            domobj.createWithFlags(START_PAUSED)
        else:
            # this covers flags = None as well as flags = 'noping'
            domobj.create()
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        logger.error("start failed")
        return 1

    while timeout:
        state = domobj.info()[0]
        expect_states = [libvirt.VIR_DOMAIN_RUNNING, libvirt.VIR_DOMAIN_PAUSED,
                         libvirt.VIR_DOMAIN_NOSTATE, libvirt.VIR_DOMAIN_BLOCKED]

        if state in expect_states:
            break

        time.sleep(10)
        timeout -= 10
        logger.info(str(timeout) + "s left")

    if timeout <= 0:
        logger.error('The domain state is not as expected, state: ' + state)
        return 1

    logger.info("Guest started")

    """If domain's current state is paused. Check if start command has
    --paused flag or managedsave has --paused flag (given flags in managedsave
    include '4'). If yes, it means domain successfully paused , then resume it.
    If not, throw error -guest state error."""

    if state == libvirt.VIR_DOMAIN_PAUSED:
        if "start_paused" in flags or "4" in flagsave:
            logger.info("Guest paused successfully ")

            try:
                domobj.resume()
                time.sleep(60)

            except libvirtError, e:
                logger.error("API error message: %s, error code is %s"
                             % (e.message, e.get_error_code()))
                logger.error("resume failed")
                return 1
            stateresume = domobj.info()[0]
            expect_states = [libvirt.VIR_DOMAIN_RUNNING,
                             libvirt.VIR_DOMAIN_NOSTATE,
                             libvirt.VIR_DOMAIN_BLOCKED]
            if stateresume not in expect_states:
                logger.error('The domain state is not equal to "paused"')
                return 1
            else:
                logger.info('Domain resume successfully')
            return 0
        else:
            logger.error("guest state error")
            return 1

    # Get domain ip and ping ip to check domain's status
    if "noping" not in flags:
        mac = utils.get_dom_mac_addr(domname)
        logger.info("get ip by mac address")
        ip = utils.mac_to_ip(mac, 180)

        logger.info('ping guest')
        if not utils.do_ping(ip, 300):
            logger.error('Failed on ping guest, IP: ' + str(ip))
            return 1

    # Check if domain' managedsave image exists,if not, return 0.
    if not domobj.hasManagedSaveImage(0) and check_savefile_remove(domname):
        logger.info("Domain %s with managedsave image successfully start"
                    % domname)
        return 0
    else:
        logger.error("Fail to start domain %s with managedsave image"
                     % domname)
        return 1
