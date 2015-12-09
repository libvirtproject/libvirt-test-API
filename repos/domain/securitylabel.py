#!/usr/bin/env python
# test securityLabel() and securityLabelList() API for libvirt

import libvirt

from libvirt import libvirtError
from src import sharedmod
from utils import utils

required_params = ('guestname',)
optional_params = {}


def check_qemu_conf(logger):
    """
       If security_driver is not equal to "selinux", report an error
    """
    GREP = "grep \"^security_driver\" /etc/libvirt/qemu.conf"
    status, output = utils.exec_cmd(GREP, shell=True)
    if status:
        return True
    else:
        if "selinux" in output[0]:
            return True
        else:
            logger.error("Not a default setting in qemu.conf")
            return False


def get_security_policy(logger):
    """
       get selinux type from host OS
    """
    SELINUX = "getenforce"
    status, output = utils.exec_cmd(SELINUX, shell=True)
    if not status:
        if output[0] == "Enforcing":
            sevalue = True
        elif output[0] == "Permissive":
            sevalue = False
        elif output[0] == "Disabled":
            sevalue = False
        else:
            logger.error("Can not find any results")
    else:
        logger.error("\"" + SELINUX + "\"" + "error")
        logger.error(output)
        return False
    return sevalue


def get_pid(name, logger):
    """
       get process id of specified domain.
    """
    PID = "ps aux |grep -v grep | grep \" -name %s\" \
           |awk '{print $2}'"
    status, output = utils.exec_cmd(PID % name, shell=True)
    if not status:
        pass
    else:
        logger.error("\"" + PID + "\"" + "error")
        logger.error(output)
        return False
    return output[0]


def get_pid_context(domain, logger):
    """
       return context of domain's pid
    """
    pid = get_pid(domain, logger)
    CONTEXT = "ls -nZd /proc/%s"
    status, output = utils.exec_cmd(CONTEXT % pid, shell=True)
    if not status:
        pass
    else:
        logger.error("\"" + CONTEXT + "\"" + "error")
        logger.error(output)
        return False
    return pid, output[0]


def check_selinux_label(api, domain, logger):
    """
       check vaules in selinux mode
    """
    pid, context = get_pid_context(domain, logger)
    logger.debug("The context of %d is %s" % (int(pid), context))
    get_enforce = get_security_policy(logger)
    if api[0] in context:
        if api[1] == get_enforce:
            logger.debug("PASS: '%s'" % api)
            return True
        else:
            logger.debug("Fail: '%s'" % api[1])
            return False
    else:
        logger.debug("Fail: '%s'" % api[0])
        return False


def check_DAC_label(api, domain, logger):
    """
       check vaules in DAC mode
    """
    tmp = []
    pid, context = get_pid_context(domain, logger)
    logger.debug("The context of %d is %s" % (int(pid), context))
    # enforcing is always false in DAC mode
    for item in api:
        tmp.append(item)
    get_enforce = False
    tmp1 = tmp[0].strip().replace("+", "")
    tmp[0] = tmp1.split(':')
    tmp1 = context.split()
    context = str(tmp1.pop(1) + " " + tmp1.pop(1)).split()
    if tmp[0] == context:
        if tmp[1] == get_enforce:
            logger.debug("PASS: '%s'" % api)
            return True
        else:
            logger.debug("Fail: '%s'" % api[1])
            return False
    else:
        logger.debug("Fail: '%s'" % api[0])
        return False

def securitylabel(params):
    """
       test APIs for securityLabel and securityLabelList in class virDomain
    """
    logger = params['logger']
    domain_name = params['guestname']
    if not check_qemu_conf(logger):
        return 1
    try:
        conn = sharedmod.libvirtobj['conn']

        if conn.lookupByName(domain_name):
            dom = conn.lookupByName(domain_name)
        else:
            logger.error("Domain %s is not exist" % domain_name)
            return 1
        if not dom.isActive():
            logger.error("Domain %s is not running" % domain_name)
            return 1

        first_label_api = dom.securityLabel()
        logger.info("The first lable is %s" % first_label_api)

        if check_selinux_label(first_label_api, domain_name, logger):
            logger.info("PASS, %s" % first_label_api)
        else:
            logger.error("FAIL, %s" % first_label_api)
            return 1

        all_label_api = dom.securityLabelList()
        logger.info("The all lable is %s" % all_label_api)
        if check_selinux_label(all_label_api[0], domain_name, logger):
            logger.info("PASS, %s" % all_label_api[0])
        else:
            logger.error("FAIL, %s" % all_label_api[0])
            return 1

        if check_DAC_label(all_label_api[1], domain_name, logger):
            logger.info("PASS, %s" % all_label_api[1])
        else:
            logger.error("FAIL, %s" % all_label_api[1])
            return 1

    except libvirtError as e:
        logger.error("API error message: %s" % e.message)
        return 1

    return 0
