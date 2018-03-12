#!/usr/bin/env python
# To test core dump of a domain

import os
import re
import sys
import time
import libvirt

from libvirt import libvirtError
from src import sharedmod
from utils import utils, process

required_params = ('guestname', 'file',)
optional_params = {}


def check_guest_status(*args):
    """Check guest current status"""
    (guestname, domobj, logger) = args

    state = domobj.info()[0]
    if state == libvirt.VIR_DOMAIN_SHUTOFF or state == libvirt.VIR_DOMAIN_SHUTDOWN:
        domobj.create()
        time.sleep(60)
        logger.debug("current guest status: %s" % state)
    # add check function
        return True
    else:
        return True


def check_guest_kernel(*args):
    """Check guest kernel version"""
    (guestname, logger) = args

    mac = utils.get_dom_mac_addr(guestname)
    logger.debug("guest mac address: %s" % mac)

    ipaddr = utils.mac_to_ip(mac, 15)
    if ipaddr is None:
        logger.error("can't get guest ip")
        return None

    logger.debug("guest ip address: %s" % ipaddr)

    kernel = utils.get_remote_kernel(ipaddr, "root", "redhat")
    logger.debug("current kernel version: %s" % kernel)

    if kernel:
        return kernel
    else:
        return None


def check_dump(*args):
    """Check dumpping core file validity"""
    (guestname, file, kernel, logger) = args

    kernel = check_guest_kernel(guestname, logger)
    (big, other) = kernel.split("-")
    small = other.split(".")
    arch = small[-1]
    pkgs = ["kernel-debuginfo-%s" % (kernel),
            "kernel-debuginfo-common-%s-%s" % (arch, kernel)]

    req_pkgs = ""
    for pkg in pkgs:
        req_pkgs = req_pkgs + pkg + ".rpm "
        cmd = "rpm -q %s" % pkg
        ret = process.run(cmd, shell=True, ignore_status=True)
        down = "wget \
                http://download.devel.redhat.com/brewroot/packages/kernel\
                /%s/%s.%s/%s/%s.rpm" % (big, small[0], small[1], arch, pkg)
        if ret.exit_status != 0:
            logger.info("Please waiting for some time,downloading...")
            ret = process.run(down, shell=True, ignore_status=True)
            if ret.exit_status != 0:
                logger.error("download failed: %s" % ret.stdout)
            else:
                logger.info(ret.stdout)
        else:
            logger.debug(ret.stdout)

    cmd = "rpm -ivh %s" % req_pkgs
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status != 0:
        logger.error("fail to install %s" % req_pkgs)
    else:
        logger.info(ret.stdout)

    if file:
        cmd = "crash /usr/lib/debug/lib/modules/%s/vmlinux %s" % \
              (kernel, file)
        logger.info("crash cmd line: %s" % cmd)
        ret = process.run(cmd, shell=True, ignore_status=True)
        if ret.exit_status == 0:
            logger.info("crash executes result: %d" % ret.exit_status)
            return 0
        else:
            logger.info("screen output information: %s" % ret.stdout)
            return 1
    else:
        logger.debug("file argument is required")
        return 1


def check_dump1(*args):
    """check whether core dump file is generated"""
    (core_file_path, logger) = args
    if os.access(core_file_path, os.R_OK):
        logger.info("core dump file path: %s is existing." % core_file_path)
        return 0
    else:
        logger.info("core dump file path: %s is NOT existing!!!" %
                    core_file_path)
        return 1


def dump(params):
    """This method will dump the core of a domain on a given file
       for analysis. Note that for remote Xen Daemon the file path
       will be interpreted in the remote host.
    """
    logger = params['logger']
    guestname = params['guestname']
    file = params['file']
    conn = sharedmod.libvirtobj['conn']

    domobj = conn.lookupByName(guestname)

    if check_guest_status(guestname, domobj, logger):
        kernel = check_guest_kernel(guestname, logger)
        if kernel is None:
            logger.error("can't get guest kernel version")
            return 1

        logger.info("dump the core of %s to file %s\n" % (guestname, file))

    try:
        domobj.coreDump(file, 0)
        retval = check_dump1(file, logger)

        if retval == 0:
            logger.info("check core dump: %d\n" % retval)
        else:
            logger.error("check core dump: %d\n" % retval)
            return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        logger.error("Error: fail to core dump %s domain" % guestname)
        return 1

    return 0


def dump_clean(params):
    """ clean testing environment """
    logger = params['logger']
    filepath = params['file']
    if os.path.exists(filepath):
        logger.info("remove dump file from core dump %s" % filepath)
        os.remove(filepath)
