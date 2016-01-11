#!/usr/bin/env python
# Test setMetadata
# Accept flag: live, config, current
# flag should be sperated with '|'
# when no flag is given, will test with flag = 0

from xml.dom import minidom

import re
import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ('guestname', )
optional_params = {'flags': 'current'}


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


def set_metadata(params):
    """set some metadata and check with xml
    """
    logger = params['logger']
    guestname = params['guestname']

    logger.info("the name of virtual machine is %s" % guestname)

    flag = parse_flag(logger, params)

    if flag == -1:
        return 1

    test_description = ("This is a test deccription\n"
                        "With multiple lines\n"
                        "\n"
                        "And empty line")

    test_title = "Test Title"
    namespace = "http://herf.derf/test"
    prefix = "ns"
    bad_namespaces = [None, 123]
    # bad_namespaces = [None, 123, '!!'] BUG
    bad_prefixs = [None, 123, "!"]
    bad_test_title = ("Test Title\n"
                      "Multiple line\n"
                      "Multiple line\n")

    test_xml = ('<?xml version="1.0" ?><TestElement>'
                '<TestElement2 TestAttribute2="TestValue2"/>'
                '<TestElement3>Test Text</TestElement3></TestElement>')


    def check_metadata(flag):
        guestxml = domobj.XMLDesc(flag)
        logger.debug("domain %s xml is :\n%s" % (guestname, guestxml))
        xml = minidom.parseString(guestxml)

        logger.info("Checking title...")
        title = xml.getElementsByTagName('title')[0]
        logger.debug(title.childNodes[0].data)
        if title.childNodes[0].data != test_title:
            return 1

        logger.info("Checking description...")
        desc = xml.getElementsByTagName('description')[0]
        logger.debug(desc.childNodes[0].data)
        if desc.childNodes[0].data != test_description:
            return 1

        logger.info("Checking misc metadata...")
        meta = xml.getElementsByTagName("ns:TestElement")[0].toxml()
        meta_namespace = re.findall(r'xmlns:ns="(\S+)"', meta)[0]
        logger.debug("xml: %s" % meta)
        meta = re.sub(r' xmlns:ns="\S+"', '', meta)
        logger.debug("namespace: %s" % namespace)
        meta = re.sub(r'<ns:', '<', meta)
        meta = re.sub(r'</ns:', '</', meta)
        meta = re.sub(r'>\s*<', '><', meta)
        test = re.sub(r'<\?xml.*\?>', '', test_xml)

        if meta_namespace != namespace:
            raise RuntimeError("Namespace doesn't match, expect: '%s', got: '%s'"
                               % (namespace, meta_namespace))
        if meta != test:
            raise RuntimeError("Metadata doesn't match, expect xml:'%s' got:'%s'"
                               % (test, meta))
        return True

    def check_empty_metadata(flag):
        guestxml = domobj.XMLDesc(flag)
        xml = minidom.parseString(guestxml)
        logger.debug("domain %s xml is :\n%s" % (guestname, guestxml))

        title = xml.getElementsByTagName('title')
        desc = xml.getElementsByTagName('description')
        meta = xml.getElementsByTagName('ns:TestElement')
        if len(title) + len(desc) + len(meta) != 0:
            raise RuntimeError("Metadata not cleared")

    try:
        logger.info("Run case with flag: %d" % flag)
        conn = sharedmod.libvirtobj['conn']
        domobj = conn.lookupByName(guestname)

        #Good cases
        logger.info("Set title")
        domobj.setMetadata(libvirt.VIR_DOMAIN_METADATA_DESCRIPTION,
                           test_description, None, None, flag)
        logger.info("Set description")
        domobj.setMetadata(libvirt.VIR_DOMAIN_METADATA_TITLE, test_title,
                           None, None, flag)
        logger.info("Try xml %s" % test_xml)
        domobj.setMetadata(libvirt.VIR_DOMAIN_METADATA_ELEMENT,
                           test_xml, prefix, namespace, flag)

        #Bad cases
        def bad_case_warpper(caseinfo, func):
            success = False
            try:
                logger.info(caseinfo)
                func()
            except Exception:
                success = True
            if success is False:
                raise RuntimeError("No exception was raised, Test failed")

        bad_case_warpper("Try bad title %s" % bad_test_title,
                         lambda:
                         domobj.setMetadata(libvirt.VIR_DOMAIN_METADATA_TITLE,
                                            bad_test_title, None, None, flag))

        bad_case_warpper("Try bad xml %s" % test_xml,
                         lambda:
                         domobj.setMetadata(libvirt.VIR_DOMAIN_METADATA_ELEMENT,
                                            test_xml+">", prefix, namespace, flag))

        map(lambda bad_namespace:
            bad_case_warpper("Try bad namespace %s" % bad_namespace,
                             lambda:
                             domobj.setMetadata(libvirt.VIR_DOMAIN_METADATA_ELEMENT,
                                                test_xml, prefix, bad_namespace, flag)),
            bad_namespaces)

        map(lambda bad_prefix:
            bad_case_warpper("Try bad namespace prefix %s" % bad_prefix,
                             lambda:
                             domobj.setMetadata(libvirt.VIR_DOMAIN_METADATA_ELEMENT,
                                                test_xml, bad_prefix, namespace, flag)),
            bad_prefixs)

        #Verify results
        if flag & libvirt.VIR_DOMAIN_AFFECT_CONFIG:
            check_metadata(libvirt.VIR_DOMAIN_XML_INACTIVE)

        if flag & libvirt.VIR_DOMAIN_AFFECT_LIVE or flag == 0:
            check_metadata(0)

        #Clear title and description
        domobj.setMetadata(libvirt.VIR_DOMAIN_METADATA_DESCRIPTION, None,
                           None, None, flag)
        domobj.setMetadata(libvirt.VIR_DOMAIN_METADATA_TITLE, None, None,
                           None, flag)
        domobj.setMetadata(libvirt.VIR_DOMAIN_METADATA_ELEMENT, None, None,
                           namespace, flag)

        #Verify title and description cleared
        if flag & libvirt.VIR_DOMAIN_AFFECT_CONFIG:
            check_empty_metadata(libvirt.VIR_DOMAIN_XML_INACTIVE)

        if flag & libvirt.VIR_DOMAIN_AFFECT_LIVE or flag == 0:
            check_empty_metadata(0)

    except libvirtError, e:
        logger.error("libvirt call failed: " + str(e))
        return 1
    except RuntimeError, e:
        logger.error("Test failed with: " + str(e))
        return 1

    return 0
