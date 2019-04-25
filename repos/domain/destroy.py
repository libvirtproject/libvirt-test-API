#!/usr/bin/env python

import time
import libvirt

from libvirt import libvirtError
from utils import utils

required_params = ('guestname',)
optional_params = {'flags': None,
                   'virt_type': 'kvm'}


def destroy(params):
    """destroy domain

       logger -- an object of utils/log.py
       guestname -- the domain name
       flags -- optional arguments:
                  noping: Don't do the ping test

       Return 0 on SUCCESS or 1 on FAILURE
    """
    logger = params['logger']
    guestname = params['guestname']
    virt_type = params.get('virt_type', 'kvm')
    flags = params.get('flags')

    try:
        if "lxc" in virt_type:
            conn = libvirt.open("lxc:///")
        else:
            conn = libvirt.open()

        # Get running domain by name
        guest_names = []
        ids = conn.listDomainsID()
        for id in ids:
            obj = conn.lookupByID(id)
            guest_names.append(obj.name())
        if guestname not in guest_names:
            logger.error("guest %s doesn't exist or isn't running." % guestname)
            return 1

        domobj = conn.lookupByName(guestname)

        if "lxc" in virt_type:
            flags = "noping"
        if not flags:
            # Get domain ip
            mac = utils.get_dom_mac_addr(guestname)
            logger.info("mac address: %s" % mac)
            ip = utils.mac_to_ip(mac, 180)
            logger.info("ip address: %s" % ip)

        # Destroy domain
        logger.info('destroy domain:')
        domobj.destroy()
        time.sleep(10)
    except libvirtError as e:
        if "Device or resource busy" in e.get_error_message():
            time.sleep(30)
            state = domobj.info()[0]
            if state == libvirt.VIR_DOMAIN_SHUTOFF or state == libvirt.VIR_DOMAIN_SHUTDOWN:
                logger.info("Guest status is shutdown.")
            else:
                logger.error("API error message: %s, error code is %s"
                             % (e.get_error_message(), e.get_error_code()))
                logger.error("failed to destroy domain")
                return 1
        elif "lxc" in virt_type and "Some processes refused to die" in e.get_error_message():
            # Add for test
            try:
                time.sleep(10)
                domobj.destroy()
            except libvirtError as e:
                logger.error("Still destroy error: %s" % e.get_error_message())
                return 1
        else:
            logger.error("API error message: %s, error code is %s"
                         % (e.get_error_message(), e.get_error_code()))
            return 1

    # Check domain status by ping ip
    if not flags:
        logger.info('ping guest')
        if utils.do_ping(ip, 30):
            logger.error('The guest is still active, IP: ' + str(ip))
            return 1
    logger.info("domain %s was destroyed successfully" % guestname)
    return 0
