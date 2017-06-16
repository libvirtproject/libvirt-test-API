#!/usr/bin/env python

import os
import signal

from utils import utils

required_params = ('guestname', 'flags')
optional_params = {}


def shutdown_request(params):
    guestname = params['guestname']
    logger = params['logger']
    flags = params['flags']

    if "host" in flags:
        cmd = "ps aux | awk '/\/usr\/libexec\/qemu-kvm -name guest=%s/{print $2}'" % guestname
        ret, out = utils.exec_cmd(cmd, shell=True)
        if ret:
            logger.error("cmd failed: %s" % cmd)
            logger.error("ret: %s, out: %s" % (ret, out))
            return 1

        os.kill(int(out[0]), signal.SIGTERM)
        logger.info("Kill guest successful.")
    elif "guest" in flags:
        mac = utils.get_dom_mac_addr(guestname)
        ip = utils.mac_to_ip(mac, 120)
        logger.info("Guest ip is %s" % ip)

        cmd = "poweroff"
        err_str = "Connection to %s closed by remote host" % ip
        ret, out = utils.remote_exec_pexpect(ip, "root", "redhat", cmd)
        if ret and err_str not in out:
            logger.error("Shutdown guest failed: %s" % out)
            return 1

        logger.info("Execute poweroff in guest successful.")
    else:
        logger.error("Don't support %s flags." % flags)
        return 1

    return 0
