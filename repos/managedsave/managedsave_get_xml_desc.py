#!/usr/bin/python
"""
To get the XMLDesc from managedsave and test if it is matching
with parameter requirement
"""

from libvirt import libvirtError
import libvirt
import time
from src import sharedmod
from lxml import etree as ET

required_params = ('guestname',)
optional_params = {'flags': 'secure',
                   }


def parse_flags(logger, params):

    flags = params.get('flags', 'secure')
    logger.info('flags is : %s' % flags)
    if flags == 'none':
        return 0
    ret = 0
    for flag in flags.split('|'):
        if flag == 'secure':
            ret = ret | libvirt.VIR_DOMAIN_XML_SECURE
        elif flag == 'inactive':
            logger.error("unsupported flags inactive now")
            return -1
        elif flag == 'update-cpu':
            logger.error("unsupported flags update-cpu now")
            return -1
        else:
            logger.error("Flags error: illegal flags %s" % flags)
            return -1
    return ret


def check_definexml(flags, guestxml, new_guestxml, guestname, logger):
    #check the xml from managedsave whether is as expected"
    tree1 = ET.XML(guestxml)
    tree2 = ET.XML(new_guestxml)
    if not flags:
        """the guestxml is not same with new_guestxml, but guestxml
           is a subset of new_guestxml
        """
        set_guestxml = set(ET.tostring(tree1).split())
        set_new_guestxml = set(ET.tostring(tree2).split())
        if (set_guestxml & set_new_guestxml) == set_guestxml:
            logger.info("get xml desc is as expected, flags is 0!")
            return 0
    elif flags & libvirt.VIR_DOMAIN_XML_SECURE:
        for elem in tree2.iter(tag='graphics'):
            if elem.attrib['passwd'] == "vnc_passwd":
                logger.info("get xml desc is as expected!,flags is secure")
                return 0

    logger.error("get xml desc is not as expected!")
    return 1


def managedsave_get_xml_desc(params):
    """
    To get the XMLDesc from managedsave and test if it is matching
    with parameter requirement
    Argument is a dictionary with two keys:
    {'logger': logger, 'guestname': guestname}

    logger -- an object of utils/log.py
    mandatory arguments: guestname -- as same the domain name
    optional arguments: flags -- additional options affecting the
                                 xml dump may be used.
                        'secure':will also include security sensitive information
                                 in the XML dump
                        'inactive':inactive tells virsh to dump domain configuration
                                   that will be used on next start of the domain as
                                   opposed to the current domain configuration
                        'update-cpu':updates domain CPU requirements according to host CPU
    notice: flags inactive & update unsupported now
    """
    guestname = params['guestname']
    logger = params['logger']

    flags = parse_flags(logger, params)
    if flags == -1:
        return 1
    conn = sharedmod.libvirtobj['conn']
    domobj = conn.lookupByName(guestname)
    """
    suspend a domain and save it's xml
    like cmd "virsh managedsave guestname"
    """
    domobj.managedSave()
    time.sleep(10)

    """get current domain configuration,it is used to compare with a
       new configuration from managedsave
    """
    guestxml = domobj.XMLDesc(0)

    try:
        new_guestxml = domobj.managedSaveGetXMLDesc(flags)
    except libvirtError as e:
        logger.info("Managedsave get xmldesc failed" + str(e))
        return 1
    ret = check_definexml(flags, guestxml, new_guestxml, guestname, logger)
    if ret:
        return 1

    logger.info("PASS")
    return 0


def managedsave_get_xml_desc_clean(params):
    guestname = params['guestname']
    logger = params['logger']
    conn = libvirt.open()
    dom = conn.lookupByName(guestname)
    state = dom.info()[0]
    if state == libvirt.VIR_DOMAIN_RUNNING:
        dom.destroy()
    dom.undefineFlags(libvirt.VIR_DOMAIN_UNDEFINE_MANAGED_SAVE)
