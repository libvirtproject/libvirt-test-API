#!/usr/bin/env python

import time

try:
    import thread
except ImportError:
    import _thread as thread

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('guestname', 'flags',)
optional_params = {}


def check_guest_status(*args):
    """Check guest current status"""
    (domobj, logger) = args
    state = domobj.info()[0]
    logger.debug("current guest status: %s" % state)

    if state == libvirt.VIR_DOMAIN_SHUTOFF or \
       state == libvirt.VIR_DOMAIN_SHUTDOWN or \
       state == libvirt.VIR_DOMAIN_BLOCKED:
        return False
    else:
        return True


def check_savefile_create(*args):
    """Check guest's managed save file be created"""

    (guestname) = args
    cmds = "ls /var/lib/libvirt/qemu/save/%s" % guestname + ".save -lh"
    logger.info("Execute cmd  %s" % cmds)
    (status, output) = utils.exec_cmd(cmds, shell=True)
    if status != 0:
        logger.error("No managed save file")
        return False
    else:
        logger.info("managed save file exists")
        return True


def get_fileflags():
    """Get the file flags of managed save file"""
    CHECK_CMD = "lsof -w /var/lib/libvirt/qemu/save/" + guestname + ".save" \
        "|awk '/libvirt_i/{print $2}'"
    GET_CMD = "cat /proc/%s/fdinfo/1|grep flags|awk '{print $NF}'"
    global fileflags
    timeout = 100
    while True:
        (status, pid) = utils.exec_cmd(CHECK_CMD, shell=True)
        if status == 0 and len(pid) == 1:
            break
        time.sleep(0.1)
        timeout -= 0.1
        if timeout <= 0:
            logger.error("Timeout waiting for save file to show up.")
            return 1

    (status, output) = utils.exec_cmd(GET_CMD % pid[0], shell=True)
    if status == 0 and len(output) == 1:
        logger.info("The flags of saved file %s " % output[0])
        if utils.isPower():
            fileflags = output[0][-6]
        else:
            fileflags = output[0][-5]
    else:
        logger.error("Fail to get the flags of saved file")
        return 1

    thread.exit_thread()


def check_fileflag(fileflags):
    """Check the file flags of managed save file if include O_DIRECT"""
    if utils.isPower():
        if int(fileflags) & 4:
            logger.info("file flags include O_DIRECT")
            return True
        else:
            logger.error("file flags doesn't include O_DIRECT")
            return False
    else:
        if int(fileflags) == 4:
            logger.info("file flags include O_DIRECT")
            return True
        else:
            logger.error("file flags doesn't include O_DIRECT")
            return False


def managedsave(params):
    """Managed save a running domain"""

    global logger
    logger = params['logger']
    global guestname
    guestname = params['guestname']
    flags = params['flags']
    global fileflags
    fileflags = ''
    #Save given flags to sharedmod.data
    sharedmod.data['flagsave'] = flags

    logger.info("The given flags are %s " % flags)
    if '|' not in flags:
        flagn = int(flags)
    else:
        # bitwise-OR of flags of managedsave
        flaglist = flags.split('|')
        flagn = 0
        for flag in flaglist:
            flagn |= int(flag)

    conn = sharedmod.libvirtobj['conn']
    domobj = conn.lookupByName(guestname)

    if not check_guest_status(domobj, logger):
        logger.error("Current guest status is shutoff")
        return 1

    try:

        logger.info("bitwise OR value of flags is %s" % flagn)

        if flagn == 0:
            logger.info("managedsave %s domain with no flag" % guestname)
        elif flagn == 1:
            logger.info("managedsave %s domain --bypass-cache" % guestname)
        elif flagn == 2:
            logger.info("managedsave %s domain --running" % guestname)
        elif flagn == 3:
            logger.info("managedsave %s domain --running --bypass-cache"
                        % guestname)
        elif flagn == 4:
            logger.info("managedsave %s domain --paused" % guestname)
        elif flagn == 5:
            logger.info("managedsave %s domain --paused --bypass-cache"
                        % guestname)
        elif flagn == 6:
            logger.error("--running and --paused are mutually exclusive")
            return 1
        elif flagn == 7:
            logger.error("--running and --paused are mutually exclusive")
            return 1
        else:
            logger.error("Wrong flags be given and fail to managedsave domain")
            return 1

        #If given flags include bypass-cache,check if bypass file system cache
        if flagn % 2 == 1:
            logger.info("Given flags include --bypass-cache")
            thread.start_new_thread(get_fileflags, ())

            # Guarantee get_fileflags shell has run before managed save
            time.sleep(30)
            domobj.managedSave(flagn)

            if check_fileflag(fileflags):
                logger.info("Bypass file system cache successfully")
            else:
                logger.error("Bypass file system cache failed")
                return 1
        else:
            domobj.managedSave(flagn)

        #Check if domain has managedsave image
        if domobj.hasManagedSaveImage(0) and \
                domobj.info()[0] == libvirt.VIR_DOMAIN_SHUTOFF and \
                check_savefile_create(guestname):
            logger.info("Domain %s managedsave successfully " % guestname)
        else:
            logger.error("Fail to managedsave domain")
            return 1

    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("Fail to managedsave %s domain" % guestname)
        return 1

    return 0
