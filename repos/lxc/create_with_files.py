#!/usr/bin/env python
"""create and start a lxc container from XML"""

import os
import time
import sys
import locale

import libvirt
from libvirt import libvirtError
from utils import utils

required_params = ('guestname',)
optional_params = {'flags': 'none',
                   }

TEST_TEXT = "TestContent-libvirt-test-api"


def get_flags(params):
    flags = params['flags']
    if flags == 'none':
        return 0
    ret = 0
    for flag in flags.split('|'):
        if flag == 'autodestroy':
            ret |= libvirt.VIR_DOMAIN_START_AUTODESTROY
        elif flag == 'paused':
            logger.info("%s is not supported yet" % flag)
        elif flag == 'bypass-cache':
            logger.info("%s is not supported yet" % flag)
        elif flag == 'force-boot':
            logger.info("%s is not supported yet" % flag)
        elif flag == 'validate':
            logger.info("%s is not supported yet" % flag)
        else:
            logger.error("Flags error:illegal flags %s" % flags)
            return -1
    return ret


def create_files(params):
    """automatic create file description"""
    variable = -1
    files = params.get('files', 'auto')

    fds = []
    default_filenum = 3

    if files == 'auto':
        #files = map(lambda x: "/tmp/libvirt-test-api-create-file-%d" % x,
        #            range(default_filenum))
        files = ["/tmp/libvirt-test-api-create-file-%d" % x for x in range(default_filenum)]
        for i in files:
            variable = variable + 1
            tmp_str = TEST_TEXT + str(variable)
            if sys.version_info[0] < 3:
                with open(i, 'w') as tmp_file:
                    tmp_file.write(tmp_str)
            else:
                with open(i, 'wb') as tmp_file:
                    encoding = locale.getpreferredencoding()
                    tmp_file.write(tmp_str.encode(encoding))

    for filename in files:
        try:
            fd = os.open(filename, os.O_RDWR | os.O_CREAT)
            fds.append(fd)
        except Exception as e:
            logger.error("Failed open file %s, %s" % (filename, str(e)))
            return -1
    return fds


def create_with_files(params):
    """Launch a defined domain. If the call succeeds the domain moves
       from the defined to the running domains pools and provide the
       ability to pass acrosss pre-opened file descriptors when starting
       lxc guests.
       {'logger': logger, 'guestname': guestname}

       logger -- an object of utils/log.py
       mandatory arguments: guestname -- same as the domain name
       optional arguments : files --files passed to init thread of guest
                              'auto' : create few files automaticly and pass them to guest
                              flags -- domain create flags
                                <none|autodestroy>
    """
    global logger
    logger = params['logger']
    global guestname
    guestname = params['guestname']

    conn = libvirt.open("lxc:///")
    domobj = conn.lookupByName(guestname)

    flags = get_flags(params)
    global files
    files = create_files(params)

    try:
        domobj.createWithFiles(files, flags)
    except libvirtError as e:
        logger.info("create domain failed" + str(e))
        return 1

    logger.info("get the mac address of vm %s" % guestname)
    mac = utils.get_dom_mac_addr(guestname, "lxc:///")
    logger.info("the mac address of vm %s is %s" % (guestname, mac))

    stream = conn.newStream(libvirt.VIR_STREAM_NONBLOCK)
    domobj.openConsole(None, stream, 0)
    encoding = locale.getpreferredencoding()
    for i in range(len(files)):
        cmd = "cat /proc/1/fd/%d  >>/tmp/libvirt_passfile_check\n" % (i + 3)
        stream.send(cmd.encode(encoding))
        time.sleep(5)
    cmd = "sync\n"
    stream.send(cmd.encode(encoding))
    stream.finish()

    #test whether or not pass-fd is successful
    with open(r'/tmp/libvirt_passfile_check', 'r') as tmp_file:
        content = tmp_file.read()
    for i in range(len(files)):
        string = "%s%s" % (TEST_TEXT, str(i))
        if string not in content:
            logger.info("pass-fd is failed!")
            return 1
    logger.info("pass-fd is successful")
    logger.info("Guest started successfully")
    logger.info("PASS")
    return 0


def create_with_files_clean(params):
    logger = params['logger']
    for i in range(len(files)):
        ret = utils.del_file("/tmp/libvirt-test-api-create-file-%d" % i, logger)
    ret = utils.del_file("/tmp/libvirt_passfile_check", logger)

    conn = libvirt.open("lxc:///")
    dom = conn.lookupByName(guestname)
    guest_state = dom.info()[0]
    if guest_state == libvirt.VIR_DOMAIN_RUNNING:
        logger.debug("destroy guest: %s." % guestname)
        time.sleep(5)
        dom.destroyFlags()
        time.sleep(3)
        dom.undefine()
        time.sleep(3)
    elif guest_state == libvirt.VIR_DOMAIN_SHUTOFF:
        time.sleep(5)
        dom.undefine()
        time.sleep(3)
