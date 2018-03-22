#!/usr/bin/env python
# To test OSType() API

from xml.dom import minidom
from src import sharedmod
from libvirt import libvirtError

required_params = ('guestname', )
optional_params = {}


def check_os_type(guestname, os_type, logger):
    """
    Check os type
    """
    path_xml = "/etc/libvirt/qemu/" + guestname + ".xml"
    doc = minidom.parse(path_xml)
    os_xml = doc.getElementsByTagName('os')[0]
    type_xml = os_xml.getElementsByTagName('type')[0]
    logger.info("get type %s from xml." % type_xml.childNodes[0].data)

    return type_xml.childNodes[0].data == os_type


def os_type(params):
    """
    Test OSType() API
    """
    logger = params['logger']
    guestname = params['guestname']

    conn = sharedmod.libvirtobj['conn']
    doms = conn.lookupByName(guestname)

    try:
        os_type = doms.OSType()
        if not check_os_type(guestname, os_type, logger):
            logger.error("FAIL: get os type %s failed." % os_type)
            return 1
        else:
            logger.info("PASS: get os type %s successful." % os_type)

    except libvirtError as e:
        logger.error("API error message: %s, error code is %s" % (e.get_error_message(), e.get_error_code()))
        return 1

    return 0
