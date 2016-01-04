#!/usr/bin/env python
# To test domain's isUpdated API
# If the guest should not be updated when this test
# was performed set parameter 'updated' to 0

import commands

import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ('guestname',)
optional_params = {'updated': 1}


def domain_is_updated(params):
    """ check the output of interfaceParameters
    """
    logger = params['logger']
    guestname = params.get('guestname')
    updated = int(params.get('updated', 1))

    logger.info("the name of guest is %s" % guestname)

    conn = sharedmod.libvirtobj['conn']

    try:
        domobj = conn.lookupByName(guestname)
        logger.info("Checking if domain is updated...")
        is_updated = domobj.isUpdated()

    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return is_updated != updated
