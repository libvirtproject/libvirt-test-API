#!/usr/bin/env python
# Test metadata
# Accept flag: live, config, current
# flag should be sperated with '|'
# when no flag is given, will test with flag = 0

from xml.dom import minidom

import re
import libvirt
from libvirt import libvirtError

required_params = ('guestname', 'type',)
optional_params = {'flags': 'current'}


def parse_flag(logger, params):
    flag = params.get('flags', 'current')
    ret = 0
    logger.info("metadata with flag %s" % flag)
    if flag == 'current':
        return libvirt.VIR_DOMAIN_AFFECT_CURRENT
    for flag in flag.split('|'):
        if flag == 'live':
            ret = ret | libvirt.VIR_DOMAIN_AFFECT_LIVE
        elif flag == 'config':
            ret = ret | libvirt.VIR_DOMAIN_AFFECT_CONFIG
        else:
            logger.error('illegal flag %s' % flag)
            return -1
    return ret


def get_metadata(params):
    """get metadata and check with xml
    """
    logger = params['logger']
    guestname = params['guestname']
    metadata_type = params['type']

    if metadata_type == "element":
        uri = "http://herp.derp/"
        logger.info("uri: %s" % uri)

    logger.info("guest name: %s" % guestname)
    logger.info("metadata type: %s" % metadata_type)

    flag = parse_flag(logger, params)
    if flag == -1:
        return 1

    def check_metadata(flag, metadata_type, info):
        guestxml = domobj.XMLDesc(flag)
        logger.debug("domain %s xml is :\n%s" % (guestname, guestxml))
        xml = minidom.parseString(guestxml)

        if metadata_type == "title":
            logger.info("Checking title...")
            title = xml.getElementsByTagName('title')[0]
            logger.debug(title.childNodes[0].data)
            if title.childNodes[0].data != info:
                return 1
        elif metadata_type == "description":
            logger.info("Checking description...")
            desc = xml.getElementsByTagName('description')[0]
            logger.debug(desc.childNodes[0].data)
            if desc.childNodes[0].data != info:
                return 1
        elif metadata_type == "element":
            logger.info("Checking misc metadata...")
            meta = xml.getElementsByTagName("blurb:foo")[0].toxml()
            meta_namespace = re.findall(r'xmlns:blurb="(\S+)"', meta)[0]
            logger.debug("xml: %s" % meta)
            meta = re.sub(r' xmlns:blurb="\S+"', '', meta)
            meta = re.sub(r'<blurb:', '<', meta)
            meta = re.sub(r'</blurb:', '</', meta)
            meta = re.sub(r' ', '', meta)
            info = re.sub(r' ', '', info)

            if meta_namespace != uri:
                raise RuntimeError("Namespace doesn't match, expect: '%s', got: '%s'"
                                   % (uri, meta_namespace))
            if meta != info:
                raise RuntimeError("Metadata doesn't match, expect xml:'%s' got:'%s'"
                                   % (info, meta))
        return True

    try:
        logger.info("Run case with flag: %d" % flag)
        conn = libvirt.open(None)
        domobj = conn.lookupByName(guestname)
        if metadata_type == "title":
            info = domobj.metadata(libvirt.VIR_DOMAIN_METADATA_TITLE, None, flag)
        elif metadata_type == "description":
            info = domobj.metadata(libvirt.VIR_DOMAIN_METADATA_DESCRIPTION, None, flag)
        elif metadata_type == "element":
            info = domobj.metadata(libvirt.VIR_DOMAIN_METADATA_ELEMENT, uri, flag)

        #Verify results
        if flag & libvirt.VIR_DOMAIN_AFFECT_CONFIG:
            check_metadata(libvirt.VIR_DOMAIN_XML_INACTIVE, metadata_type, info)

        if flag & libvirt.VIR_DOMAIN_AFFECT_LIVE or flag == 0:
            check_metadata(0, metadata_type, info)

    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return 1
    except RuntimeError as e:
        logger.error("Test failed with: " + str(e))
        return 1

    return 0
