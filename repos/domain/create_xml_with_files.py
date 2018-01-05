#!/usr/bin/env python
"""create and start a lxc container from XML and provide the ability to
   pass across pre-opened file descriptors when starting LXC guests.
"""

import os
import time

import shutil
import libvirt
import functools
from libvirt import libvirtError
from utils import utils

NONE = 0
START_PAUSED = 1
START_AUTODESTROY = 2

required_params = ('guestname',)
optional_params = {'memory': 1048576,
                   'vcpu': 1,
                   'macaddr': '52:54:00:97:e4:28',
                   'uuid': 'e1d8f470-a362-11e7-a9bb-3c970e93647c',
                   'imagepath': '/var/lib/libvirt/images/libvirt-ci.qcow2',
                   'diskpath': '/var/lib/libvirt/images/libvirt-test-api',
                   'imageformat': 'qcow2',
                   'virt_type': 'lxc',
                   'flags': 'none',
                   'files': 'auto',
                   'xml': 'xmls/lxc.xml',
                   }

TEST_TEXT = "TestContent-libvirt-test-api"


def create_files(logger, params):
    variable = -1
    files = params.get('files', 'auto')

    fds = []
    default_filenum = 3

    if files == 'auto':
        files = map(lambda x: "/tmp/libvirt-test-api-create-file-%d" % x,
                    range(default_filenum))
        for i in files:
            variable = variable + 1
            with open(i, 'w') as tmp_file:
                tmp_file.write(TEST_TEXT + str(variable))

    for filename in files:
        try:
            fd = os.open(filename, os.O_RDWR | os.O_CREAT)
            fds.append(fd)
        except Exception as e:
            logger.error("Failed open file %s, %s" % (filename, str(e)))
            return -1
    return fds


def parse_flags(logger, params):

    flags = params.get('flags', 'none')
    ret = 0
    for flag in flags.split('|'):
        if flag == 'start_paused':
            ret = ret | START_PAUSED
        elif flag == 'start_autodestroy':
            ret = ret | START_AUTODESTROY
        elif flag == 'none':
            ret = ret | NONE
        else:
            logger.error("Flags error: illegal flags %s" % flags)
            return -1
    return ret


def check_dom_state(domobj):
    state = domobj.info()[0]
    expect_states = [libvirt.VIR_DOMAIN_RUNNING, libvirt.VIR_DOMAIN_NOSTATE,
                     libvirt.VIR_DOMAIN_BLOCKED]

    if state in expect_states:
        return 1
    return 0


def create_xml_with_files(params):
    """create and start a lxc container from  XML  and provide the ability to
       pass across pre-opened file descriptors whe starting LXC guests.
        Argument is a dictionary with two keys:
        {'logger': logger, 'guestname': guestname}

        logger -- an object of utils/log.py
        mandatory arguments : guestname -- same as the domain name
        optional arguments : files -- files passed to init thread of guest
                                'auto': create few files automaticly and pass them to guest
                             flags -- domain create flags
                                <none|start_paused|start_autodestroy>
    """
    global state
    global files
    guestname = params['guestname']
    logger = params['logger']
    xmlstr = params['xml']
    macaddr = params.get('macaddr', '52:54:00:97:e4:28')
    uuid = params.get('uuid', 'e1d8f470-a362-11e7-a9bb-3c970e93647c')
    xmlstr = xmlstr.replace('UUID', uuid)
    imagepath = params.get('imagepath', '/var/lib/libvirt/images/libvirt-ci.qcow2')
    logger.info("using image %s" % imagepath)
    diskpath = params.get('diskpath', '/var/lib/libvirt/images/libvirt-test-api')
    logger.info("disk image is %s" % diskpath)
    shutil.copyfile(imagepath, diskpath)
    os.chown(diskpath, 107, 107)

    flags = parse_flags(logger, params)
    files = create_files(logger, params)
    if flags == -1:
        return 1

    conn = libvirt.open("lxc:///")

    # Create domain from xml
    try:
        domobj = conn.createXMLWithFiles(xmlstr, files, flags)
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        logger.error("fail to create domain %s" % guestname)
        return 1

    if flags & START_PAUSED:
        state = domobj.info()[0]
        if state == libvirt.VIR_DOMAIN_PAUSED:
            logger.info("guest start with state paused successfully")
            return 0
        else:
            logger.error("guest state error")
            return 1
    if flags & START_AUTODESTROY:
        state = domobj.info()[0]
        if state == libvirt.VIR_DOMAIN_AUTODESTROY:
            logger.info("guest start with state autodestroy successfully")
            return 0
        else:
            logger.error("guest start error")
            return 1

    ret = utils.wait_for(functools.partial(check_dom_state, domobj), 600)
    if ret is None:
        logger.error('The domain state is not as expected, state: ' + state)
        return 1

    logger.info("get the mac address of vm %s" % guestname)
    mac = utils.get_dom_mac_addr(guestname, "lxc:///")
    logger.info("the mac address of vm %s is %s" % (guestname, mac))

    stream = conn.newStream(libvirt.VIR_STREAM_NONBLOCK)
    domobj.openConsole(None, stream, 0)
    for i in range(len(files)):
        cmd = "cat /proc/1/fd/%d  >>/tmp/libvirt_passfile_check\n" % (i + 3)
        stream.send(cmd)
        time.sleep(5)
    cmd = "sync\n"
    stream.send(cmd)
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


def create_xml_with_files_clean(params):
    logger = params['logger']
    guestname = params['guestname']

    for i in range(len(files)):
        ret = utils.del_file("/tmp/libvirt-test-api-create-file-%d" % i, logger)
    ret = utils.del_file("/tmp/libvirt_passfile_check", logger)

    conn = libvirt.open("lxc:///")
    dom = conn.lookupByName(guestname)
    if dom.isActive():
        logger.debug("destroy guest: %s." % guestname)
        dom.destroy()
