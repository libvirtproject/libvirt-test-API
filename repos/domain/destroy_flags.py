#!/usr/bin/env python

import time
import libvirt
from libvirt import libvirtError
from src import sharedmod
from utils import utils
import commands

required_params = ('guestname', )
optional_params = {'flags': 'graceful',
                   }


def parse_flags(logger, params):

    flags = params.get('flags', 'none')
    if flags == 'none':
        return 0

    ret = 0
    if flags == 'graceful':
        ret = libvirt.VIR_DOMAIN_DESTROY_GRACEFUL
    else:
        logger.error("Flags error illegal flags %s" % flags)
        return -1
    return ret


def set_signal_ignore(guestname, logger):
    #make guest process block sigterm signal by stopping this guest qemu process
    cmd = "ps -ef | grep %s | grep qemu | head \
            -n 1 | awk '{print $2}' " % guestname
    (ret, out) = commands.getstatusoutput(cmd)
    logger.debug("guest qemu process pid is %s" % out)
    if ret:
        logger.error("fail to get the guest process pid")
        return 1

    cmd = "kill -19 %s" % out

    (ret, out) = commands.getstatusoutput(cmd)
    if ret:
        logger.error("fail to stop the guest process")
        return 1
    return 0


def destroy_flags(params):
    """destroy domain with flags
       {'guestname': guestname}

       logger -- an object of utils/log.py
       guestname -- the domain name
       flags -- option arguments:
                graceful:terminal the guest gracefully by SIGTERM.
                    virDomainDestroyFlags will instead return an error if
                    the guest doesn't terminate by the end of the timeout;
                    at that time, the management application can decide if
                    calling again without VIR_DOMAIN_DESTROY_GRACEFUL is
                    appropriate.
                none:terminal the guest graceful by SIGGTERM and SIGKILL
       Return 0 on SUCCESS or 1 on FAILURE
    """

    logger = params['logger']
    guestname = params['guestname']

    flags = parse_flags(logger, params)
    if flags == -1:
        return 1

    conn = sharedmod.libvirtobj['conn']
    domobj = conn.lookupByName(guestname)

    logger.info("get the mac address of vm %s " % guestname)
    mac = utils.get_dom_mac_addr(guestname)

    logger.info("the mac address of vm %s is %s" % (guestname, mac))
    logger.info("get ip by mac address")
    ip = utils.mac_to_ip(mac, 180)
    logger.info("the ip address of vm %s is %s" % (guestname, ip))

    ret = set_signal_ignore(guestname, logger)
    if ret:
        return 1

    logger.info("destroy vm %s now" % guestname)

    #call destroyFlags(0) after failing to call destroyFlags with graceful
    for i in range(2):
        try:
            domobj.destroyFlags(flags)
        except libvirtError, e:
            #get a error when 'graceful' in flags and guest qemu process stop
            if (flags == libvirt.VIR_DOMAIN_DESTROY_GRACEFUL and
                    "Device or resource busy" in str(e)):
                logger.info("guest process block sigterm signal successfully")
                flags = 0
                continue
            else:
                logger.error("destroy guest failed: " + str(e))
                return 1
        break

    timeout = 600
    while timeout:
        time.sleep(10)
        timeout -= 10
        if utils.do_ping(ip, 0):
            logger.info(str(timeout) + "s lfet")
        else:
            logger.info("vm %s destroy successfully" % guestname)
            break
        if timeout == 0:
            logger.info("fail to destroy %s" % guestname)
            return 1

    logger.info("PASS")
    return 0
