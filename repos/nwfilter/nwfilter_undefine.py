#!/usr/bin/env python

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
        if cmp(nwfilter,nwfilter_uuidstr) and cmp(nwfilter_uuidstr,\
                                                  nwfilter_uuid):
            # Undefine the nwfilter
            nwfilter.undefine()
            # Check if the nwfiler list includes the undefined nwfilter
            if nwfiltername not in conn.listNWFilters():
                logger.info("Successfully undefine the nwfilter %s" % \
                        nwfiltername)
                return 0
        else:
            logger.error("Failed to undefine the nwfilter %s" % nwfiltername)
            return 1

    except libvirtError, e:
        logger.error("API error message: %s" % e.message)
        return 1

    return 0
