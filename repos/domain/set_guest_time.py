#!/usr/bin/evn python
# To test setting guest time

import time
import libvirt

from libvirt import libvirtError
from src import sharedmod
from utils import utils
from utils.utils import get_xml_value

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
    seconds = int(params['seconds'])
    nseconds = int(params.get('nseconds', 0))
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
    xml_path = "/domain/devices/interface/mac/@address"
    mac = get_xml_value(domobj, xml_path)
    if len(mac) == 0:
        logger.error("Failed to get guest's MAC address")
        return 1
    else:
        logger.info("guest's MAC is %s" % mac)

    ipaddr = utils.mac_to_ip(mac[0], 180)
    if ipaddr is None:
        logger.error("Failed to get guest's IP address")
        return 1
    else:
        logger.info("guest's IP is %s" % ipaddr)

    try:
        domobj.setTime({'seconds': seconds, 'nseconds': nseconds}, flags)
        ret, out = utils.remote_exec_pexpect(ipaddr, username, userpassword, GET_TIME)
        sec = int(out)
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
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
