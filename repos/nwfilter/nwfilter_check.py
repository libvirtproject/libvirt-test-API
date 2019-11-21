#!/usr/bin/env python

import time

from libvirt import libvirtError
from utils import utils
from xml.dom import minidom

from src import sharedmod

required_params = ('nwfiltername', 'guestname',)
optional_params = {}

EBTABLES = "ebtables -t nat -L %s"


def get_ebtables(params, logger):
    """ Get the output of ebtables """
    cmd = EBTABLES % params
    (status, output) = utils.exec_cmd(cmd, shell=True)
    logger.info("Execute command:" + cmd)
    if status:
        logger.error("Executing " + cmd + " failed")
        logger.error(output)
        return False
    logger.info("ebtables list: %s" % output)
    return output


def check_ebtables(*args):
    """ Check the ebtables """
    (nwfiltername, conn, logger) = args

    #Get the filter' attribute value
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
    in_chain_str = "Bridge chain: " + in_vnet_chain
    out_chain_str = "Bridge chain: " + out_vnet_chain

    if direction == "inout":
        in_list = get_ebtables(in_vnet_chain, logger)
        out_list = get_ebtables(out_vnet_chain, logger)
        if (in_chain_str in in_list[-2] and
                out_chain_str in out_list[-2] and
                action in in_list[-1] and
                action in out_list[-1]):
            return True
        else:
            return False
    elif direction == "in":
        out_list = get_ebtables(out_vnet_chain, logger)
        if (out_chain_str in out_list[-2] and
                action in out_list[-1]):
            return True
        else:
            return False
    elif direction == "out":
        in_list = get_ebtables(in_vnet_chain, logger)
        if (in_chain_str in in_list[-2] and
                action in in_list[-1]):
            return True
        else:
            return False


def nwfilter_check(params):
    """Check the nwfilter via checking ebtales"""
    logger = params['logger']
    nwfiltername = params['nwfiltername']
    guestname = params['guestname']
    domain_nwfilter_xml = ""

    conn = sharedmod.libvirtobj['conn']
    domobj = conn.lookupByName(guestname)

    try:

        #Create the nwfilter's element and append it to domain xml
        domxml = domobj.XMLDesc(0)
        domain_parsedxml = minidom.parseString(domxml)
        domain_ifxml = domain_parsedxml.getElementsByTagName("interface")
        filterxml = domain_parsedxml.createElement("filterref")
        filterxml.setAttribute("filter", nwfiltername)
        domain_ifxml[0].appendChild(filterxml)

        #Destroy the domain and redefine it with nwfilter
        domobj.destroy()
        time.sleep(5)
        domobj.undefine()

        #Define the new domain with the nwfilter
        dom_nwfilter = conn.defineXML(domain_parsedxml.toxml())
        logger.debug("The xml of new defined domain with nwfilter %s" %
                     dom_nwfilter.XMLDesc(0))

        #Start the new defined domain
        dom_nwfilter.create()
        time.sleep(5)

        if check_ebtables(nwfiltername, conn, logger):
            logger.info("Successfully create nwfilter")
            return 0
        else:
            logger.error("Failed to create nwfilter")
            return 1

    except libvirtError as e:
        logger.error("API error message: %s" % e.get_error_message())
        return 1

    return 0
