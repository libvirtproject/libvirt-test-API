#!/usr/bin/python
"""
To get the XMLDesc from a saved state file and test if it is matching
with parameter requirement
"""

from libvirt import libvirtError
import libvirt
from src import sharedmod
from lxml import etree as ET
from utils import utils
from repos.domain import domain_common

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
        else:
            logger.error("Flags error: illegal flags %s" % flags)
            return -1
    return ret


def check_definexml(flags, guestxml, new_guestxml, guestname, logger):
    #check the xml from a saved state file whether is as expected"
    tree1 = ET.XML(guestxml)
    tree2 = ET.XML(new_guestxml)
    if not flags:
        #the guestxml is not same with new_guestxml, but guestxml
        #is a subset of new_guestxml
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


def save_image_get_xml_desc(params):
    """
    To get the XMLDesc from a saved state file and test if it is matching
    with parameter requirement
    Argument is a dictionary with two keys:
    {'logger': logger, 'guestname': guestname}

    logger -- an object of utils/log.py
    mandatory arguments: guestname -- as same the domain name
    optional arguments: flags -- additional options affecting the
                                 xml dump may be used.
                        'secure':will also include security sensitive information
                                 in the XML desc
    """
    guestname = params['guestname']
    logger = params['logger']

    flags = parse_flags(logger, params)
    if flags == -1:
        return 1
    conn = sharedmod.libvirtobj['conn']
    domobj = conn.lookupByName(guestname)

    #shutdown a domain and save it's state
    #like cmd "virsh save guestname"
    domobj.save("/tmp/%s.save" % guestname)

    #get current domain configuration,it is used to compare with a
    #new configuration from a saved state file
    guestxml = domobj.XMLDesc(0)

    try:
        new_guestxml = conn.saveImageGetXMLDesc("/tmp/%s.save" % guestname, flags)
    except libvirtError as e:
        logger.info("saveimage get xmldesc failed" + str(e))
        return 1

    ret = check_definexml(flags, guestxml, new_guestxml, guestname, logger)
    if ret:
        return 1

    logger.info("PASS")
    return 0


def save_image_get_xml_desc_clean(params):
    guestname = params['guestname']
    logger = params['logger']
    conn = libvirt.open()
    domain_common.guest_clean(conn, guestname, logger)
    utils.del_file("/tmp/%s.save" % guestname, logger)
