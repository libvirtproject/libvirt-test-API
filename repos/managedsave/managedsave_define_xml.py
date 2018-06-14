#!/usr/bin/env python
"""To update the definition of domain stored in a saved state file and restart by this file.
"""

from libvirt import libvirtError
import libvirt
import time
from src import sharedmod
from utils import utils
import functools
from xml.dom import minidom

required_params = ('guestname',)
optional_params = {'flags': 'save_running',
                   }


def parse_flags(logger, params):
    flags = params.get('flags', 'save_paused')

    ret = 0
    if flags == 'save_running':
        ret = libvirt.VIR_DOMAIN_SAVE_RUNNING
    elif flags == 'save_paused':
        ret = libvirt.VIR_DOMAIN_SAVE_PAUSED
    elif flags == 'none':
        ret = None
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


def managedsave_define_xml(params):
    """
    To update the definition of domain stored in a saved state file and restart by this file.
    Argument is a dictionary with two keys:
    {'logger': logger, 'guestname': guestname}

    logger -- an object of utils/log.py
    mandatory arguments : guestname -- as same the domain name
    optional arguments : flags -- will override the default saved into the managedsave
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

    """suspend a domain and save its memory contents to a file on disk.
       like cmd "virsh managedsave guestname"
    """
    domobj.managedSave()
    time.sleep(10)

    #get guest'xml
    guestxml = domobj.XMLDesc(0)

    #alter some portions of the domain XML
    dom = minidom.parseString(guestxml)
    tree_root = dom.documentElement
    vnc = tree_root.getElementsByTagName('graphics')[0]
    vnc.setAttribute('port', '5901')
    vnc.setAttribute('autoport', 'no')
    guestxml = tree_root.toprettyxml()
    logger.debug("minidom string is %s\n" % guestxml)

    try:
        domobj.managedSaveDefineXML(guestxml, flags)
    except libvirtError as e:
        logger.info("Save definexml failed" + str(e))
        return 1

    domobj.create()
    if flags == libvirt.VIR_DOMAIN_SAVE_PAUSED:
        state = libvirt.VIR_DOMAIN_PAUSED
    else:
        state = libvirt.VIR_DOMAIN_RUNNING
    ret = utils.wait_for(functools.partial(check_dom_state, domobj), 600)

    if ret != state:
        logger.error('The domain state is not as expected, state: %d' % state)
        return 1

    if state == libvirt.VIR_DOMAIN_PAUSED:
        domobj.resume()

    guestxml = domobj.XMLDesc(0)
    logger.debug("New guestxml is \n %s" % guestxml)

    dom = minidom.parseString(guestxml)
    tree_root = dom.documentElement
    vnc = tree_root.getElementsByTagName('graphics')[0]
    if vnc.getAttribute('port') != '5901' or vnc.getAttribute('autoport') != 'no':
        logger.error("The domain is not changed as expected")
        return 1
    logger.info("The domain is changed as expected")
    logger.info("PASS")
    return 0


def managedsave_define_xml_clean(params):
    guestname = params['guestname']
    logger = params['logger']
    conn = libvirt.open()
    dom = conn.lookupByName(guestname)
    state = dom.info()[0]
    if state == libvirt.VIR_DOMAIN_RUNNING:
        dom.destroy()
    dom.undefineFlags(libvirt.VIR_DOMAIN_UNDEFINE_MANAGED_SAVE)
