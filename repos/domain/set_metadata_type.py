#!/usr/bin/env python
# Test setMetadata
# Accept flag: live, config, current
# flag should be sperated with '|'
# when no flag is given, will test with flag = 0

import re
import libvirt

from xml.dom import minidom
from libvirt import libvirtError


required_params = ('guestname', 'metadata_type',)
optional_params = {'flags': 'current',
                   'nsuri': None
                   }


def parse_flag(logger, params):
    flag = params.get('flags', 'current')
    ret = 0
    logger.info("setMetadata with flag %s" % flag)
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


def set_metadata_type(params):
    """set some metadata and check with xml
    """
    logger = params['logger']
    guestname = params['guestname']
    metadata_type = params['metadata_type']
    nsuri = params.get('nsuri', None)

    logger.info("guest name: %s" % guestname)
    logger.info("metadata type: %s" % metadata_type)
    logger.info("nsuri: %s" % nsuri)

    flag = parse_flag(logger, params)
    if flag == -1:
        return 1

    test_title = "Test Title"
    test_description = "Test Description"
    test_xml = '<derp xmlns:foobar="http://foo.bar/"></derp>'

    def check_metadata(flag, metadata_type):
        guestxml = domobj.XMLDesc(flag)
        logger.debug("domain %s xml is :\n%s" % (guestname, guestxml))
        xml = minidom.parseString(guestxml)

        if metadata_type == "title":
            logger.info("Checking title...")
            title = xml.getElementsByTagName('title')[0]
            logger.debug(title.childNodes[0].data)
            if title.childNodes[0].data != test_title:
                return 1
        elif metadata_type == "description":
            logger.info("Checking description...")
            desc = xml.getElementsByTagName('description')[0]
            logger.debug(desc.childNodes[0].data)
            if desc.childNodes[0].data != test_description:
                return 1
        elif metadata_type == "element":
            logger.info("Checking misc metadata...")
            meta = xml.getElementsByTagName("ns:derp")[0].toxml()
            meta_namespace = re.findall(r'xmlns:ns="(\S+)"', meta)[0]
            logger.debug("xml: %s" % meta)
            meta = re.sub(r' xmlns:ns="\S+"', '', meta)
            meta = re.sub(r'<ns:', '<', meta)
            meta = re.sub(r'/>', '></derp>', meta)

            if meta_namespace != nsuri:
                raise RuntimeError("Namespace doesn't match, expect: '%s', got: '%s'"
                                   % (nsuri, meta_namespace))
            if meta != test_xml:
                raise RuntimeError("Metadata doesn't match, expect xml:'%s' got:'%s'"
                                   % (test_xml, meta))
        return True

    try:
        logger.info("Run case with flag: %d" % flag)
        conn = libvirt.open(None)
        domobj = conn.lookupByName(guestname)

        if metadata_type == "title":
            domobj.setMetadata(libvirt.VIR_DOMAIN_METADATA_TITLE, test_title,
                               None, None, flag)
        elif metadata_type == "description":
            domobj.setMetadata(libvirt.VIR_DOMAIN_METADATA_DESCRIPTION,
                               test_description, None, None, flag)
        elif metadata_type == "element":
            logger.info("Try xml %s" % test_xml)
            domobj.setMetadata(libvirt.VIR_DOMAIN_METADATA_ELEMENT,
                               test_xml, 'ns', nsuri, flag)

        #Verify results
        if flag & libvirt.VIR_DOMAIN_AFFECT_CONFIG:
            check_metadata(libvirt.VIR_DOMAIN_XML_INACTIVE, metadata_type)

        if flag & libvirt.VIR_DOMAIN_AFFECT_LIVE or flag == 0:
            check_metadata(0, metadata_type)

        # clear
        if metadata_type == "title":
            domobj.setMetadata(libvirt.VIR_DOMAIN_METADATA_TITLE, None,
                               None, None, flag)
        elif metadata_type == "description":
            domobj.setMetadata(libvirt.VIR_DOMAIN_METADATA_DESCRIPTION,
                               None, None, None, flag)
        elif metadata_type == "element":
            domobj.setMetadata(libvirt.VIR_DOMAIN_METADATA_ELEMENT,
                               None, None, nsuri, flag)

    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return 1
    except RuntimeError as e:
        logger.error("Test failed with: " + str(e))
        return 1

    return 0
