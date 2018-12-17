#!/usr/bin/env python

import operator

from libvirt import libvirtError
from src import sharedmod

required_params = ('nwfiltername',)
optional_params = {}


def nwfilter_undefine(params):
    """Undefine the specified nwfilter"""
    logger = params['logger']
    nwfiltername = params['nwfiltername']
    conn = sharedmod.libvirtobj['conn']

    try:
        nwfilter = conn.nwfilterLookupByName(nwfiltername)
        uuidstr = nwfilter.UUIDString()
        uuid = nwfilter.UUID()
        # Lookup by nwfilter's uuid string
        nwfilter_uuidstr = conn.nwfilterLookupByUUIDString(uuidstr)
        # Lookup by nwfilter's uuid
        nwfilter_uuid = conn.nwfilterLookupByUUID(uuid)

        # Check if the nwfilter lookup by name/uuid/uuidstr is the same one
        if (operator.eq(nwfilter.name(), nwfilter_uuidstr.name()) and
                operator.eq(nwfilter_uuidstr.name(), nwfilter_uuid.name())):
            # Undefine the nwfilter
            nwfilter.undefine()
            # Check if the nwfiler list includes the undefined nwfilter
            if nwfiltername not in conn.listNWFilters():
                logger.info("Successfully undefine the nwfilter %s" %
                            nwfiltername)
                return 0
        else:
            logger.error("Failed to undefine the nwfilter %s" % nwfiltername)
            return 1

    except libvirtError as e:
        logger.error("API error message: %s" % e.get_error_message())
        return 1

    return 0
