#!/usr/bin/evn python
# To test domain fsfreeze

import time
import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ('guestname',)
optional_params = {'mountpoint': ''}


def check_frozen_num(mp, num):
    """check the number of frozen fs"""
    if mp is None:
        return True

    if len(mp) == num:
        return True
    else:
        return False


def parse_mountpoint(mp):
    """parse the argument mountpoint"""
    if mp is None:
        return None

    return [p.strip() for p in mp.split(',')]


def check_guest_status(domobj):
    """Check guest current status"""
    state = domobj.info()[0]
    if state == libvirt.VIR_DOMAIN_SHUTOFF or \
            state == libvirt.VIR_DOMAIN_SHUTDOWN:
        # add check function
        return False
    else:
        return True


def domain_fsfreeze(params):
    """domain fsfreeze test function"""
    logger = params['logger']
    guestname = params['guestname']
    mountpoint = parse_mountpoint(params.get('mountpoint'))

    conn = sharedmod.libvirtobj['conn']

    domobj = conn.lookupByName(guestname)

    # Check domain block status
    if check_guest_status(domobj):
        pass
    else:
        domobj.create()
        time.sleep(90)

    try:
        num = domobj.fsFreeze(mountpoint, 0)
        logger.info("freeze %s fs" % num)

        if check_frozen_num(mountpoint, num):
            logger.info("Check frozen fs num: pass")
        else:
            logger.error("Check frozen fs num: failed")
            return 1

    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    return 0
