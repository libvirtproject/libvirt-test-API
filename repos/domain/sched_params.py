#!/usr/bin/evn python
# To test domain scheduler parameters

import time
import libvirt

from src import sharedmod
from utils import utils, process

required_params = ('guestname', 'capshares',)
optional_params = {}


def check_guest_status(domobj):
    """Check guest current status"""
    state = domobj.info()[0]
    if state == libvirt.VIR_DOMAIN_SHUTOFF or state == libvirt.VIR_DOMAIN_SHUTDOWN:
        domobj.create()
        time.sleep(30)
    # Add check function
        return True
    else:
        return True


def check_sched_params(*args):
    """Check scheduler parameters validity after setting"""
    hypervisor, dicts, guestname, domobj = args
    sched_dict = {}
    if hypervisor == "xen":
        cmd = "xm sched-credit -d %s" % guestname
        out = process.system_output(cmd, shell=True, ignore_status=True)
        sched_dict = eval(out)
        if sched_dict['weight'] == dicts['weight'] and \
                sched_dict['cap'] == dicts['cap']:
            return 0
        else:
            return 1
    if hypervisor == "kvm":
        sched_dict = domobj.schedulerParameters()
        if sched_dict['cpu_shares'] == dicts['cpu_shares']:
            return 0
        else:
            return 1


def sched_params(params):
    """Setting scheduler parameters, argument params is a
       dictionary data type.which includes 'weight' and 'cap'
       keys, by assigning different value to 'weight' and 'cap'
       to verify validity of the result
    """
    hypervisor = utils.get_hypervisor()

    logger = params['logger']
    guestname = params['guestname']
    conn = sharedmod.libvirtobj['conn']

    domobj = conn.lookupByName(guestname)

    if check_guest_status(domobj):
        sched_params = domobj.schedulerParameters()
        logger.info("original scheduler parameters: %s\n" % sched_params)

    if 'xen' in hypervisor:
        str_weight = params['weight']
        str_cap = params['cap']
        for wgt in eval(str_weight):
            for cap in eval(str_cap):
                dicts = {'weight': wgt, 'cap': cap}
                logger.info("setting scheduler parameters: %s" % dicts)
                domobj.setSchedulerParameters(dicts)
                sched_params = domobj.schedulerParameters()
                logger.info("current scheduler parameters: %s\n" % sched_params)

                retval = check_sched_params(hypervisor, dicts,
                                            guestname, domobj)
                if retval != 0:
                    return 1
    elif 'kvm' in hypervisor:
        cpu_shares = int(params['cpushares'])
        dicts = {'cpu_shares': cpu_shares}
        logger.info("setting scheduler parameters: %s" % dicts)
        domobj.setSchedulerParameters(dicts)
        sched_params = domobj.schedulerParameters()
        logger.info("current scheduler parameters: %s\n" % sched_params)
        retval = check_sched_params(hypervisor, dicts,
                                    guestname, domobj)
        if retval != 0:
            return 1
    else:
        logger.error("unsupported hypervisor type: %s" % hypervisor)
        return 1

    return 0
