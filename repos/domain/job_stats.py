#!/usr/bin/env python

import os
import threading
import time
import libvirt
import functools

from libvirt import libvirtError
from src import sharedmod
from utils.utils import parse_flags, version_compare
from utils import utils, process
from repos.domain import domain_common

required_params = ('guestname',)
optional_params = {'vm_state': None,
                   'flags': None,
                   'username': 'root',
                   'password': None,
                   'target_machine': None
                   }

DUMP_PATH = "/tmp/test-api-job-stats.dump"
SAVE_PATH = "/tmp/test-api-job-stats.save"

def domain_dump(dom, logger):
    if os.path.exists(DUMP_PATH):
        os.remove(DUMP_PATH)

    logger.info("start to dump job.")
    try:
        dom.coreDump(DUMP_PATH, 0)
    except libvirtError as e:
        logger.error("info: %s, code: %s" % (e.get_error_message(), e.get_error_code()))

    return


def domain_save(dom, logger):
    if os.path.exists(SAVE_PATH):
        os.remove(SAVE_PATH)

    logger.info("start to save job.")
    try:
        dom.save(SAVE_PATH)
    except libvirtError as e:
        logger.error("info: %s, code: %s" % (e.get_error_message(), e.get_error_code()))

    return


def clean_src_env(guestname, logger):
    srcconn = libvirt.open()
    if domain_common.guest_clean(srcconn, guestname, logger):
        logger.error("clean src env failed.")
        return 1
    return 0


def clean_dst_env(guestname, target, logger):
    dsturi = "qemu+ssh://%s/system" % target
    dstconn = libvirt.open(dsturi)
    if domain_common.guest_clean(dstconn, guestname, logger):
        logger.error("clean dst env failed.")
        return 1
    return 0


def check_dom_state(domobj, expect_states):
    state = domobj.info()[0]
    if state != expect_states:
        return 1
    return 0


def domain_migrate(dom, target, username, passwd, logger):
    #generate ssh key pair
    ret = domain_common.ssh_keygen(logger)
    if ret:
        logger.error("failed to generate RSA key")
        return 1
    #setup ssh tunnel with target machine
    ret = domain_common.ssh_tunnel(target, username, passwd, logger)
    if ret:
        logger.error("faild to setup ssh tunnel with target %s" % target)
        return 1

    process.run("ssh-add", shell=True, ignore_status=True)

    dsturi = "qemu+ssh://%s/system" % target

    logger.info("start to migrate.")
    try:
        dstconn = libvirt.open(dsturi)
        dom.migrate(dstconn, libvirt.VIR_MIGRATE_LIVE|libvirt.VIR_MIGRATE_UNSAFE, None, None, 0)
    except libvirtError as e:
        logger.error("info: %s, code: %s" % (e.get_error_message(), e.get_error_code()))
        return 1

    ret = utils.wait_for(functools.partial(check_dom_state, dom, 5), 100)
    if ret:
        logger.info("The domain state is not as expected")
        return 1

    return 0


def check_page_size(target_machine, username, password, info, logger):
    """check libvirt3.9 new feature
       add the print of page size in jobinfo of migrate
    """
    page_size = info['memory_page_size']
    cmd = "getconf PAGESIZE"
    logger.info("the memory page size of print in jobstats is %s" % page_size)
    ret, output = utils.remote_exec_pexpect(target_machine, username,
                                            password, cmd)
    if ret:
        logger.error("failed to get page size of machine %s" % target_machine)
        return 1
    logger.info("the page size of machine %s is %s" % (target_machine, output))
    if page_size != int(output):
        logger.error("the page size in print is incorrect")
        return 1
    return 0


def job_stats(params):
    """Test get job stats
    """
    guestname = params['guestname']
    logger = params['logger']
    vm_state = params.get('vm_state', None)
    flags = parse_flags(params, param_name='flags')
    target = params.get('target_machine', None)
    username = params.get('uesrname', 'root')
    passwd = params.get('password', None)

    logger.info("guestname: %s" % guestname)
    logger.info("flags: %s" % flags)
    logger.info("vm_state: %s" % vm_state)

    try:
        conn = sharedmod.libvirtobj['conn']
        domobj = conn.lookupByName(guestname)
        if flags == libvirt.VIR_DOMAIN_JOB_STATS_COMPLETED:
            if vm_state == "save":
                domain_save(domobj, logger)
            elif vm_state == "dump":
                domain_dump(domobj, logger)
            elif vm_state == "migrate":
                domain_migrate(domobj, target, username, passwd, logger)
            info = domobj.jobStats(flags)
        else:
            if vm_state == "save":
                ret = threading.Thread(target=domain_save, args=(domobj, logger))
                ret.start()
                timeout = 100
                while True:
                    info = domobj.jobStats(flags)
                    if info['type'] == 2:
                        break
                    time.sleep(0.1)
                    timeout -= 0.1
                    if timeout <= 0:
                        logger.error("Timeout waiting get right job type.")
                        return 1
            elif vm_state == "dump":
                ret = threading.Thread(target=domain_dump, args=(domobj, logger))
                ret.start()
                timeout = 100
                while True:
                    info = domobj.jobStats(flags)
                    if info['type'] == 2:
                        break
                    time.sleep(0.1)
                    timeout -= 0.1
                    if timeout <= 0:
                        logger.error("Timeout waiting get right job type.")
                        return 1
            else:
                info = domobj.jobStats(flags)
        time.sleep(10)
        logger.info("job stats: %s" % info)
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    if flags == libvirt.VIR_DOMAIN_JOB_STATS_COMPLETED:
        if version_compare("libvirt", 3, 9, 0, logger):
            if vm_state == "migrate":
                ret = check_page_size(target, username, passwd, info, logger)
                if ret:
                    clean_src_env(guestname, logger)
                    clean_dst_env(guestname, target, logger)
                    logger.error("Check page size failed.")
                    return 1
                clean_src_env(guestname, logger)
                clean_dst_env(guestname, target, logger)

        if version_compare("libvirt", 2, 5, 0, logger):
            if vm_state == "save":
                if info['operation'] == 2:
                    logger.info("PASS: check save operation ok.")
                else:
                    logger.error("FAIL: check save operation failed.")
                    return 1
            elif vm_state == "dump":
                if info['operation'] == 8:
                    logger.info("PASS:  check dump operation ok.")
                else:
                    logger.error("FAIL: check dump operation failed.")
                    return 1
            elif vm_state == "migrate":
                if info['operation'] == 5:
                    logger.info("PASS: check migrate operation ok.")
                else:
                    logger.error("FAIL: check migrate operation failed.")
                    return 1

        if info['type'] == 3:
            logger.info("PASS: check type ok.")
        else:
            logger.error("FAIL: check type failed.")
            return 1
    else:
        if vm_state == "save" or vm_state == "dump":
            if info['type'] == 2:
                logger.info("PASS: check %s type ok." % vm_state)
            else:
                logger.error("FAIL: check %s type failed." % vm_state)
                return 1
        else:
            if info['type'] == 0:
                logger.info("PASS: check type ok.")
            else:
                logger.error("FAIL: check type failed.")
                return 1

    return 0


def job_stats_clean(params):
    vm_state = params.get('vm_state', None)
    guestname = params['guestname']
    logger = params['logger']
    flags = parse_flags(params, param_name='flags')
    target = params.get('target_machine', None)

    if vm_state == "save":
        if os.path.exists(SAVE_PATH):
            os.remove(SAVE_PATH)
    elif vm_state == "dump":
        if os.path.exists(DUMP_PATH):
            os.remove(DUMP_PATH)
    elif vm_state == "migrate" and flags == libvirt.VIR_DOMAIN_JOB_STATS_COMPLETED:
        clean_dst_env(guestname, target, logger)
    clean_src_env(guestname, logger)
