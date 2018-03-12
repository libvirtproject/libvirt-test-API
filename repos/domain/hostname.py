#!/usr/bin/env python
# To test "virsh hostname" command

from utils import process

required_params = ()
optional_params = {}

VIRSH_HOSTNAME = "virsh hostname"


def hostname(params):
    """check virsh hostname command
    """
    logger = params['logger']

    ret = process.run(VIRSH_HOSTNAME, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("executing " + "\"" + VIRSH_HOSTNAME + "\"" + " failed")
        return 1
    virsh_ret = ret.stdout
    logger.info("the output of " + "\"" + VIRSH_HOSTNAME + "\"" + " is %s" % virsh_ret)

    ret = process.run("hostname", shell=True, ignore_status=True)
    if status:
        logger.error("executing " + "\"" + "hostname" + "\"" + " failed")
        return 1

    host_ret = ret.stdout
    if virsh_ret[:-1] != host_ret:
        logger.error("the output of " + VIRSH_HOSTNAME + " is not right")
        return 1
    else:
        logger.info(VIRSH_HOSTNAME + " testing succeeded")

    return 0
