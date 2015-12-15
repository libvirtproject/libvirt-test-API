#!/usr/bin/env python
# To test "virsh hostname" command

import os
import sys
import re
import commands

required_params = ()
optional_params = {}

VIRSH_HOSTNAME = "virsh hostname"


def hostname(params):
    """check virsh hostname command
    """
    logger = params['logger']

    status, virsh_ret = commands.getstatusoutput(VIRSH_HOSTNAME)
    if status:
        logger.error("executing " + "\"" + VIRSH_HOSTNAME + "\"" + " failed")
        return 1
    logger.info("the output of " + "\"" + VIRSH_HOSTNAME + "\"" + " is %s" % virsh_ret)

    status, host_ret = commands.getstatusoutput("hostname")
    if status:
        logger.error("executing " + "\"" + "hostname" + "\"" + " failed")
        return 1

    if virsh_ret[:-1] != host_ret:
        logger.error("the output of " + VIRSH_HOSTNAME + " is not right")
        return 1
    else:
        logger.info(VIRSH_HOSTNAME + " testing succeeded")

    return 0
