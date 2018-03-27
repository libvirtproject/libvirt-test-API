#!/usr/bin/evn python
# To test guest time

import time
import libvirt

from libvirt import libvirtError
from src import sharedmod
from utils import utils
from utils.utils import get_xml_value

required_params = ('guestname', 'username', 'userpassword',)
optional_params = {}

GET_TIME = 'date +%s'
DELTA = 3


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


def guest_time(params):
    """ test guest time
    """
    logger = params['logger']
    guestname = params['guestname']
    username = params['username']
    userpassword = params['userpassword']

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
        ret, t1 = utils.remote_exec_pexpect(ipaddr, username, userpassword, GET_TIME)
        t2 = domobj.getTime()['seconds']
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    if check_guest_time(int(t1), t2):
        logger.info("checking guest time: %s" % t2)
    else:
        logger.error("checking guest time: failed")
        return 1

    return 0
