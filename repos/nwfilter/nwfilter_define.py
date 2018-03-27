#! /usr/bin/env python

import os

from libvirt import libvirtError
from src import sharedmod

nwfilter_path = "/etc/libvirt/nwfilter/%s.xml"

required_params = ('nwfiltername', 'chain', 'action', 'direction')
optional_params = {'xml': 'xmls/nwfilter.xml', }


def nwfilter_define(params):
    """ Define network filters."""
    logger = params['logger']
    conn = sharedmod.libvirtobj['conn']
    xmlstr = params['xml']
    nwfiltername = params['nwfiltername']
    chain = params['chain']
    action = params['action']
    direction = params['direction']

    xmlstr = xmlstr.replace('NWFILTERNAME', nwfiltername)
    xmlstr = xmlstr.replace('CHAIN', chain)
    xmlstr = xmlstr.replace('ACTION', action)
    xmlstr = xmlstr.replace('DIRECTION', direction)
    try:
        logger.info("nwfiltername:%s chain:%s action:%s direction:%s" %
                    (nwfiltername, chain, action, direction))
        logger.info("The nwfilter's xml is %s" % xmlstr)

        # Define the nwfilter with given attribute value from nwfilter.conf"""
        conn.nwfilterDefineXML(xmlstr)
        nwfilterxml = conn.nwfilterLookupByName(nwfiltername).XMLDesc(0)

        if nwfiltername in conn.listNWFilters():
            logger.info("The nwfilter list includes the defined nwfilter")
            if os.path.exists(nwfilter_path % nwfiltername):
                logger.info("Successfully define the nwfilter %s" %
                            nwfiltername)
                return 0
            else:
                logger.error("Fail to define the nwfilter %s" % nwfiltername)
                return 1
        else:
            logger.error("FAIL: nwfilter list doesn't include %s" % nwfiltername)
            return 1

    except libvirtError as e:
        logger.error("API error message: %s" % e.get_error_message())
        return 1

    return 0
