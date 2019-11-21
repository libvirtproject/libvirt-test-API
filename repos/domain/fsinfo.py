#!/usr/bin/env python

import libvirt
from libvirt import libvirtError
import lxml
import lxml.etree
from utils import utils

required_params = ('guestname', 'username', 'userpassword',)
optional_params = {'conn': 'qemu:///system'}


def get_guest_mac(vm):
    tree = lxml.etree.fromstring(vm.XMLDesc(0))
    set = tree.xpath("/domain/devices/interface/mac")

    for n in set:
        return n.attrib['address']

    return False


def check_agent_status(vm):
    """ make sure agent is okay to use """

    tree = lxml.etree.fromstring(vm.XMLDesc(0))

    set = tree.xpath("//channel[@type='unix']/target[@name='org.qemu.guest_agent.0']")
    for n in set:
        if n.attrib['state'] == 'connected':
            return True

    return False


def check_fsinfo(ipaddr, username, userpasswd, fsinfo, logger):
    """ equal the fsinfo from libvirt and we get in guest mountinfo """

    cmd = "cat /proc/self/mountinfo"
    ret, mounts_needparse = utils.remote_exec_pexpect(ipaddr, username, userpasswd, cmd)
    mounts = utils.parse_mountinfo(mounts_needparse)

    for n in fsinfo:
        mountdir = n[0]
        name = n[1]
        type1 = n[2]
        target = n[3][0]
        found = 0

        for i in mounts:
            if mountdir == i['mountdir']:
                found = 1
                if i['mounttype'] != type1:
                    logger.error("Fail: mount type is not equal: libvirt: %s but we get: %s" % (type1, i['mounttype']))
                    return False

        if found == 0:
            logger.error("Fail: cannot find %s in guest mount info" % mountdir)
            return False

    return True


def fsinfo(params):
    """
       test API for fsInfo in class virDomain
    """

    logger = params['logger']
    guest = params['guestname']
    username = params['username']
    userpasswd = params['userpassword']

    try:
        conn = libvirt.open(params['conn'])

        logger.info("get connection to libvirtd")
        vm = conn.lookupByName(guest)
        logger.info("test guest name: %s" % guest)

        if not check_agent_status(vm):
            logger.error("guest agent is not connected")
            return 1

        fsinfo = vm.fsInfo()
        logger.info("get guest filesystem information")

        mac = get_guest_mac(vm)
        if not mac:
            logger.error("cannot get guest interface mac")
            return 1

        ipaddr = utils.mac_to_ip(mac, 180)
        if not ipaddr:
            logger.error("cannot get guest IP")
            return 1

        if not check_fsinfo(ipaddr, username, userpasswd, fsinfo, logger):
            return 1

    except libvirtError as e:
        logger.error("API error message: %s" % e.get_error_message())
        return 1

    return 0
