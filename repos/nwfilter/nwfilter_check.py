#!/usr/bin/env python
import time
import xml.dom.minidom

from libvirt import libvirtError
from utils import utils
from xml.dom import minidom

from src import sharedmod

required_params = ('nwfiltername', 'guestname',)
optional_params = {}

EBTABLES = "ebtables -t nat -L"


def get_ebtables():
    """ Get the output of ebtables """
    (status, output) = utils.exec_cmd(EBTABLES, shell=True)
    logger.info("Execute command:" + EBTABLES)
    ebtables_list = []

    if status:
        logger.error("Executing " + EBTABLES + " failed")
        logger.error(output)
        return False
    else:
        for i in range(len(output)):
            ebtables_list.append(output[i])
        logger.info("Get the output of ebtables list: %s"
                    % ebtables_list)

    return ebtables_list


def check_ebtables(*args):
    """ Check the ebtables """
    (nwfiltername, conn) = args
    ebtables_list = get_ebtables()

    # Get the filter' attribute value
    nwfilter_xml = conn.nwfilterLookupByName(nwfiltername).XMLDesc(0)
    nwfilter_parsedxml = minidom.parseString(nwfilter_xml)
    chain = nwfilter_parsedxml.getElementsByTagName("filter")[0].\
        getAttribute("chain")
    rule = nwfilter_parsedxml.getElementsByTagName("rule")[0]
    action = rule.getAttribute("action").upper()
    direction = rule.getAttribute("direction")
    logger.info("The nwfilter chain:%s ,action:%s ,direction:%s " %
                (chain, action, direction))
    in_vnet_chain = "I-vnet0-" + chain
    out_vnet_chain = "O-vnet0-" + chain

    if cmp(direction, "inout") == 0:
        if len(ebtables_list) == 21 and in_vnet_chain in ebtables_list[-5]\
                and out_vnet_chain in ebtables_list[-2] \
                and action in ebtables_list[-1] \
                and action in ebtables_list[-4]:
            return True
        else:
            return False
    elif cmp(direction, "in") == 0:
        if len(ebtables_list) == 14 and out_vnet_chain in ebtables_list[-2]\
                and action in ebtables_list[-1]:
            return True
        else:
            return False

    elif cmp(direction, "out") == 0:
        if len(ebtables_list) == 14 and in_vnet_chain in ebtables_list[-2] \
                and action in ebtables_list[-1]:
            return True
        else:
            return False


def nwfilter_check(params):
    """Check the nwfilter via checking ebtales"""
    global logger
    logger = params['logger']
    nwfiltername = params['nwfiltername']
    guestname = params['guestname']
    domain_nwfilter_xml = ""

    conn = sharedmod.libvirtobj['conn']
    domobj = conn.lookupByName(guestname)

    try:

        # Create the nwfilter's element and append it to domain xml
        domxml = domobj.XMLDesc(0)
        domain_parsedxml = minidom.parseString(domxml)
        domain_ifxml = domain_parsedxml.getElementsByTagName("interface")
        filterxml = domain_parsedxml.createElement("filterref")
        filterxml.setAttribute("filter", nwfiltername)
        domain_ifxml[0].appendChild(filterxml)

        # Destroy the domain and redefine it with nwfilter
        domobj.destroy()
        time.sleep(5)
        domobj.undefine()

        # Define the new domain with the nwfilter
        dom_nwfilter = conn.defineXML(domain_parsedxml.toxml())
        logger.debug("The xml of new defined domain with nwfilter %s" %
                     dom_nwfilter.XMLDesc(0))

        # Start the new defined domain
        dom_nwfilter.create()
        time.sleep(5)

        if check_ebtables(nwfiltername, conn):
            logger.info("Successfully create nwfilter")
            return 0
        else:
            logger.error("Failed to create nwfilter")
            return 1

    except libvirtError as e:
        logger.error("API error message: %s" % e.get_error_message())
        return 1

    return 0
