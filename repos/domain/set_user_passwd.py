#!/usr/bin/env python

import libvirt
from libvirt import libvirtError
import lxml
import lxml.etree
import crypt
from utils import utils

required_params = ('guestname', 'username', 'userpassword',)
optional_params = {'conn': 'qemu:///system', 'flags': '', }


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


def create_new_user(ipaddr, newusername, username, userpasswd, logger):
    cmd = "useradd %s" % newusername
    ret, retinfo = utils.remote_exec_pexpect(ipaddr, username, userpasswd, cmd)
    if ret == 0 or "already exists" in retinfo:
        return 0
    else:
        logger.error("Fail: cannot create a new user: %s" % retinfo)
        return 1


def verify_cur_user(ipaddr, username, userpasswd):
    cmd = "whoami"
    ret, retinfo = utils.remote_exec_pexpect(ipaddr, username, userpasswd, cmd)

    return ret


def set_user_passwd(params):
    """
       test API for setUserPassword in class virDomain
    """

    logger = params['logger']
    guest = params['guestname']
    username = params['username']
    userpasswd = params['userpassword']

    if 'flags' in params:
        if params['flags'] == 'encrypted':
            flags = libvirt.VIR_DOMAIN_PASSWORD_ENCRYPTED
        else:
            flags = 0
    else:
        flags = 0

    try:
        if 'conn' in params:
            conn = libvirt.open(params['conn'])
        else:
            conn = libvirt.open(optional_params['conn'])

        logger.info("get connection to libvirtd")
        vm = conn.lookupByName(guest)
        logger.info("test guest name: %s" % guest)

        if not check_agent_status(vm):
            logger.error("guest agent is not connected")
            return 1

        mac = get_guest_mac(vm)
        if not mac:
            logger.error("cannot get guest interface mac")
            return 1

        ipaddr = utils.mac_to_ip(mac, 180)
        if not ipaddr:
            logger.error("cannot get guest IP")
            return 1

        if flags > 0:
            passwd = crypt.crypt("123456", crypt.mksalt(crypt.METHOD_SHA512))
        else:
            passwd = "123456"

        if create_new_user(ipaddr, "usertestapi", username, userpasswd, logger) != 0:
            return 1

        vm.setUserPassword("usertestapi", passwd, flags)

        if verify_cur_user(ipaddr, "usertestapi", "123456") != 0:
            logger.error("cannot login guest via new user")
            return 1

    except libvirtError as e:
        logger.error("API error message: %s" % e.get_error_message())
        return 1

    return 0
