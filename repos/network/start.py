#!/usr/bin/evn python
# Start a network

import time
import commands

from libvirt import libvirtError
from src import sharedmod
from utils.utils import exec_cmd, version_compare

required_params = ('networkname',)
optional_params = {}


def start(params):
    """activate a defined network"""

    logger = params['logger']
    networkname = params['networkname']
    logger.info("the name of virtual network to be activated is %s" %
                networkname)

    if version_compare("libvirt", 3, 2, 0, logger):
        cmd = "ip route | grep \'default via\' | awk \'{print $5}\'"
        logger.debug("cmd: %s" % cmd)
        ret, out = exec_cmd(cmd, shell=True)
        logger.debug("interface: %s" % out[0])
        if ret != 0:
            logger.error("fail to get interface.")
            logger.error("ret: %s, out: %s" % (ret, out))
            return 1

        if len(out) != 0:
            cmd = "/sbin/sysctl -w net.ipv6.conf.%s.accept_ra=2" % out[0]
        else:
            cmd = "/sbin/sysctl -w net.ipv6.conf.all.accept_ra=2"
        logger.debug("cmd: %s" % cmd)
        ret, out = exec_cmd(cmd, shell=True)
        if ret != 0:
            logger.error("cmd failed: %s" % cmd)
            logger.error("ret: %s, out: %s" % (ret, out))
            return 1

    conn = sharedmod.libvirtobj['conn']

    net_defined_list = conn.listDefinedNetworks()

    if networkname not in net_defined_list:
        logger.error("virtual network %s doesn't exist \
                      or is active already." % networkname)
        return 1
    else:
        netobj = conn.networkLookupByName(networkname)
        netxmldesc = netobj.XMLDesc(0)
        logger.debug("the xml description of the virtual network is %s" %
                     netxmldesc)

    try:
        logger.info("begin to activate virtual network %s" % networkname)
        netobj.create()
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        logger.error("fail to destroy domain")
        return 1

    net_activated_list = conn.listNetworks()

    if networkname not in net_activated_list:
        logger.error(
            "virtual network %s failed to be activated." %
            networkname)
        return 1
    else:
        shell_cmd = "virsh net-list --all"
        (status, text) = commands.getstatusoutput(shell_cmd)
        logger.debug("the output of 'virsh net-list --all' is %s" % text)

    logger.info("activate the virtual network successfully.")
    time.sleep(3)

    return 0
