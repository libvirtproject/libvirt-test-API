#!/usr/bin/evn python
# To test setting guest time

import time
import libxml2

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('guestname', 'username', 'userpassword', 'seconds',)
optional_params = {'flags': 0, 'nseconds': 0}

GET_TIME = 'date +%s'
DELTA = 30


def parse_flags(flags):
    """ parse flags
    """
    if flags == 'sync':
        return 1
    elif flags == 0:
        return 0
    else:
        return -1


def get_guest_mac(dom):
    """ get guest's MAC address by parsing XML
    """
    doc = libxml2.parseDoc(dom.XMLDesc())
    cont = doc.xpathNewContext()
    macs = cont.xpathEval("/domain/devices/interface/mac/@address")
    if macs is None:
        return None
    mac = macs[0].content
    return mac


def check_guest_status(domobj):
    """ check guest current status
    """
    state = domobj.info()[0]
    if state == libvirt.VIR_DOMAIN_SHUTOFF or \
            state == libvirt.VIR_DOMAIN_SHUTDOWN:
        return False
    else:
        return True


def check_guest_time(t1, t2):
    """ check result, the acceptable error within delta
    """
    diff = abs(t1 - t2)
    if diff > DELTA:
        return False
    else:
        return True


def set_guest_time(params):
    """ test setting guest time
    """
    logger = params['logger']
    guestname = params['guestname']
    username = params['username']
    userpassword = params['userpassword']
    seconds = long(params['seconds'])
    nseconds = long(params.get('nseconds', 0))
    f = params.get('flags', 0)
    flags = parse_flags(f)

    if flags == -1:
        logger.error("unrecongnized flags: %s" % f)
        return 1

    conn = sharedmod.libvirtobj['conn']

    domobj = conn.lookupByName(guestname)

    # Check domain status
    if check_guest_status(domobj):
        pass
    else:
        domobj.create()
        time.sleep(90)

    # get guest MAC
    mac = get_guest_mac(domobj)
    if mac is None:
        logger.error("Failed to get guest's MAC address")
        return 1
    else:
        logger.info("guest's MAC is %s" % mac)

    ipaddr = utils.mac_to_ip(mac, 180)
    if mac is None:
        logger.error("Failed to get guest's IP address")
        return 1
    else:
        logger.info("guest's IP is %s" % ipaddr)

    try:
        domobj.setTime({'seconds': seconds, 'nseconds': nseconds}, flags)

        sec = long(utils.remote_exec(ipaddr, username, userpassword, GET_TIME))

    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    if flags == 1:
        logger.info("guest time is synchronized to %s" % sec)
        return 0

    if check_guest_time(seconds, sec):
        logger.info("guest time is set to %s: pass" % seconds)
    else:
        logger.error("guest time %s is not matched with what we expected %s" %
                     (sec, seconds))
        return 1

    return 0
