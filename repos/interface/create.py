#!/usr/bin/env python

from libvirt import libvirtError

from src import sharedmod
from utils import utils
from utils import process

required_params = ('ifacename',)
optional_params = {}


def display_current_interface(conn):
    """Display current host interface information"""
    logger.debug("current active host interface number: %s "
                 % conn.numOfInterfaces)
    logger.debug("current active host interface list: %s "
                 % conn.listInterfaces())
    logger.debug("current defined host interface number: %s "
                 % conn.numOfDefinedInterfaces())
    logger.debug("current defined host interface list: %s "
                 % conn.listDefinedInterfaces())


def check_create_interface(ifacename):
    """Check creating interface result, it will can ping itself
       if create interface is successful.
    """
    hostip = utils.get_ip_address(ifacename)
    logger.debug("interface %s ip address: %s" % (ifacename, hostip))
    ping_cmd = "ping -c 4 -q %s" % hostip
    ret = process.run(ping_cmd, shell=True, ignore_status=True)
    logger.debug("ping cmd: exit status=%s, out=%s" % (ret.exit_status, ret.stdout))
    if ret.exit_status == 0:
        logger.debug("can ping itself")
        return True
    else:
        logger.error("can't ping itself")
        return False


def create(params):
    """Activate specific interface, argument params is dictionary type, and
       includes 'ifacename' key, which is a host interface name, e.g 'eth0'
    """
    global logger
    logger = params['logger']
    ifacename = params['ifacename']

    try:
        hostip = utils.get_ip_address(ifacename)
        logger.error("interface %s is running" % ifacename)
        logger.debug("interface %s ip address: %s" % (ifacename, hostip))
        return 1
    except:
        logger.info("interface %s is deactive" % ifacename)

    conn = sharedmod.libvirtobj['conn']
    ifaceobj = conn.interfaceLookupByName(ifacename)
    display_current_interface(conn)

    try:
        ifaceobj.create(0)
        logger.info("create host interface %s" % ifacename)
        display_current_interface(conn)
        if check_create_interface(ifacename):
            logger.info("create host interface %s is successful" % ifacename)
        else:
            logger.error("fail to check create interface")
            return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("fail to create interface %s" % ifacename)
        return 1

    return 0
