#!/usr/bin/env python
from libvirt import libvirtError
from src import sharedmod


required_params = ()
optional_params = {}


def connection_isEncrypted(params):
    """Test if the connection to the hypervisor is encrypted

       Argument is a dictionary with one keys:
       {'logger': logger}

       Reture 0 on SUCCESS or 1 on FAILURE
    """

    logger = params['logger']

    conn = sharedmod.libvirtobj['conn']
    logger.info('Test if the connection to the hypervisor is encrypted')
    try:
        conn.isEncrypted()
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1
    logger.info('PASS')
    return 0
