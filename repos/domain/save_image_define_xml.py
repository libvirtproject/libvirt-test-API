#!/usr/bin/env python
"""To update the definition of domain stored in a saved state file.
"""

from libvirt import libvirtError
import libvirt
from src import sharedmod
from utils import utils
import functools
from xml.dom import minidom

required_params = ('guestname',)
optional_params = {'flags': 'save_running',
                   }


def parse_flags(logger, params):
    flags = params.get('flags', 'save_paused')
    logger.info("flags: %s" % flags)

    ret = 0
    if flags == 'save_running':
        ret = libvirt.VIR_DOMAIN_SAVE_RUNNING
    elif flags == 'save_paused':
        ret = libvirt.VIR_DOMAIN_SAVE_PAUSED
    elif flags == 'none':
        ret = 0
    else:
        logger.error("Flags error illegal flags %s" % flags)
        return -1
    return ret


def check_dom_state(domobj):
    state = domobj.info()[0]
    expect_states = [libvirt.VIR_DOMAIN_PAUSED, libvirt.VIR_DOMAIN_RUNNING]
    if state in expect_states:
        return state
    return 0


def save_image_define_xml(params):
    """
    To update the definition of domain stored in a saved state file.
    Argument is a dictionary with two keys:
    {'logger': logger, 'guestname': guestname}

    logger -- an object of utils/log.py
    mandatory arguments : guestname -- as same the domain name
    optional arguments : flags -- will override the default saved state
                         'save_running' : guest start in running state
                         'save_paused' : guest start in paused state
                         'none' : guest start in default state
    """

    guestname = params['guestname']
    logger = params['logger']

    flags = parse_flags(logger, params)
    if flags == -1:
        return 1

    conn = sharedmod.libvirtobj['conn']
    domobj = conn.lookupByName(guestname)

    logger.info("get the mac address of vm %s" % guestname)
    mac = utils.get_dom_mac_addr(guestname)
    logger.info("the mac address of vm %s is %s" % (guestname, mac))

    #save a domain state to a file
    #like cmd "virsh save guestname file"
    domobj.save("/tmp/%s.save" % guestname)

    #get guest'xml
    guestxml = domobj.XMLDesc(0)

    #alter some portions of the domain XML
    dom = minidom.parseString(guestxml)
    tree_root = dom.documentElement
    vnc = tree_root.getElementsByTagName('boot')[0]
    vnc.setAttribute('dev', 'cdrom')
    guestxml = tree_root.toprettyxml()
    logger.debug("minidom string is %s\n" % guestxml)

    try:
        conn.saveImageDefineXML('/tmp/%s.save' % guestname, guestxml, flags)
    except libvirtError as e:
        logger.info("Save image definexml failed" + str(e))
        return 1

    conn.restore('/tmp/%s.save' % guestname)
    if flags == libvirt.VIR_DOMAIN_SAVE_PAUSED:
        state = libvirt.VIR_DOMAIN_PAUSED
    else:
        state = libvirt.VIR_DOMAIN_RUNNING
    ret = utils.wait_for(functools.partial(check_dom_state, domobj), 600)

    if ret != state:
        logger.error('The domain state is not as expected, state: %d' % state)
        return 1

    guestxml = domobj.XMLDesc(0)
    logger.debug("New guestxml is \n %s" % guestxml)

    if state == libvirt.VIR_DOMAIN_PAUSED:
        domobj.resume()

    dom = minidom.parseString(guestxml)
    tree_root = dom.documentElement
    vnc = tree_root.getElementsByTagName('boot')[0]
    if vnc.getAttribute('dev') != 'cdrom':
        logger.error("The domain is not changed as expected")
        return 1
    logger.info("The domain is changed as expected")
    logger.info("PASS")
    return 0


def save_image_define_xml_clean(params):
    guestname = params['guestname']
    logger = params['logger']
    ret = utils.del_file("/tmp/%s.save" % guestname, logger)
