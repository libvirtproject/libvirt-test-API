#!/usr/bin/env python

import os
import time
import libvirt

from libvirt import libvirtError
from utils import utils

required_params = ('guestname',)
optional_params = {'flags': 'none',
                   'files': None,
                   'wait_time': 40,
                   'virt_type': 'kvm',
                   }

test_text = "Test Content - libvirt-test-api"
noping = False


def parse_flags(logger, params):
    global noping

    flags = params.get('flags', 'none')
    logger.info('start with flags :%s' % flags)
    if flags == 'none':
        return None
    ret = 0
    for flag in flags.split('|'):
        if flag == 'start_paused':
            ret = ret | libvirt.VIR_DOMAIN_START_PAUSED
        elif flag == 'auto_destory':
            ret = ret | libvirt.VIR_DOMAIN_START_AUTODESTROY
        elif flag == 'bypass_cache':
            ret = ret | libvirt.VIR_DOMAIN_START_BYPASS_CACHE
        elif flag == 'force_boot':
            ret = ret | libvirt.VIR_DOMAIN_START_FORCE_BOOT
        elif flag == 'validate':  # This flag is not supported by some driver
            ret = ret | libvirt.VIR_DOMAIN_START_VALIDATE
        elif flag == 'none':
            ret = ret | libvirt.VIR_DOMAIN_START_VALIDATE
            logger.error("Flags error: Can't specify none with any other flags simultaneously")
            return -1
        elif flag == 'noping':
            noping = True
        else:
            logger.error("Flags error: illegal flags %s" % flags)
            return -1
    return ret


def create_files(logger, params):
    files = params.get('files', 'none')
    if files == 'none':
        return None

    logger.info('start with files :%s' % files)
    fds = []
    default_filenum = 3

    if files == 'auto':
        #files = map(lambda x: "/tmp/libvirt-test-api-start-file-%d" % x,
        #            range(default_filenum))
        files = ["/tmp/libvirt-test-api-start-file-%d" % x for x in range(default_filenum)]
        for i in files:
            with open(i, 'w') as tmp_file:
                tmp_file.write(test_text)
    else:
        files = files.split("|")

    for filename in files:
        try:
            fd = os.open(filename, os.O_RDWR | os.O_CREAT)
            fds.append(fd)
        except Exception as e:
            logger.error("Failed open file %s, %s" % (filename, str(e)))
            return -1
    return fds


def start(params):
    """Start domain

        Argument is a dictionary with two keys:
        {'logger': logger, 'guestname': guestname}

        logger -- an object of utils/log.py
        mandatory arguments : guestname -- same as the domain name
        optional arguments : files -- files passed to init thread of guest
                                'none': no files passwd to guest.
                                'auto': create few files automaticly and pass them to guest
                                filename: specify files to be passed
                             flags -- domain create flags
                                <none|start_paused|auto_destory|bypass_cache|force_boot|noping>

        Return 0 on SUCCESS or 1 on FAILURE
    """
    global noping

    domname = params['guestname']
    logger = params['logger']
    wait_time = params.get('wait_time', 40)
    virt_type = params.get('virt_type', 'kvm')
    flags = parse_flags(logger, params)
    files = create_files(logger, params)

    if flags == -1:
        return 1
    if "lxc" in virt_type:
        conn = libvirt.open("lxc:///")
        noping = True
    else:
        conn = libvirt.open()
    domobj = conn.lookupByName(domname)

    timeout = 600
    logger.info('start domain')

    try:
        if files is None:
            if flags is None:
                flags = 0
                domobj.create()
            else:
                domobj.createWithFlags(flags)
        else:
            if flags is None:
                flags = 0
                domobj.createWithFiles(files, 0)
            else:
                domobj.createWithFiles(files, flags)

    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("start failed")
        return 1

    if flags & libvirt.VIR_DOMAIN_START_PAUSED:
        state = domobj.info()[0]
        if state == libvirt.VIR_DOMAIN_PAUSED:
            logger.info("guest start with state paused successfully")
            return 0
        else:
            logger.error("guest state error")
            return 1

    while timeout:
        state = domobj.info()[0]
        expect_states = [libvirt.VIR_DOMAIN_RUNNING, libvirt.VIR_DOMAIN_NOSTATE, libvirt.VIR_DOMAIN_BLOCKED]

        if state in expect_states:
            break

        time.sleep(10)
        timeout -= 10
        logger.info(str(timeout) + "s left")

    if timeout <= 0:
        logger.error('The domain state is not as expected, state: ' + state)
        return 1

    ipaddr = None
    # Get domain ip and ping ip to check domain's status
    if not (flags & libvirt.VIR_DOMAIN_START_PAUSED or flags &
            libvirt.VIR_DOMAIN_START_VALIDATE) and not noping:
        if "lxc" in virt_type:
            mac = utils.get_dom_mac_addr(domname, "lxc:///")
        else:
            mac = utils.get_dom_mac_addr(domname)
        logger.info("the mac address of vm %s is %s" % (domname, mac))
        logger.info("get ip by mac address")
        ipaddr = utils.mac_to_ip(mac, 180)
        logger.info("the ip address of vm %s is %s" % (domname, ipaddr))
        logger.info('ping guest')
        if not utils.do_ping(ipaddr, 300):
            logger.error('Failed on ping guest, IP: ' + str(ipaddr))
            return 1

    if files is not None and not noping:
        username = 'root'
        password = 'redhat'
        cmd = 'cat /proc/1/fd/%d'
        for i in len(files):
            (ret, output) = utils.remote_exec_pexpect(ipaddr, username, password,
                                                      cmd % (i + 3))

            if test_text != output:
                logger.err("File in guest doesn't match file in hosts!")
                return 1

    if noping:
        time.sleep(wait_time)

    logger.info("Guest started successfully")
    logger.info("PASS")
    return 0
