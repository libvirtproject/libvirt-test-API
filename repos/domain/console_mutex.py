#!/usr/bin/env python
# To test console mutual exclusivity

import libvirt
from libvirt import libvirtError
from exception import TestError

from src import sharedmod

required_params = ('guestname',)
optional_params = {'device': 'serial0'}


def console_mutex(params):
    """Attach to console"""
    logger = params['logger']
    guest = params['guestname']
    device = params.get('device', 'serial0')

    try:
        conn = sharedmod.libvirtobj['conn']
        dom = conn.lookupByName(guest)

        if not dom.isActive():
            raise TestError("Guest '%s' is not active" % guest)

        logger.info("Creating stream object")
        stream = conn.newStream(0)

        logger.info("Forcibly open console on domain")
        dom.openConsole(device, stream, libvirt.VIR_DOMAIN_CONSOLE_FORCE)

        logger.info("Creating another stream object")
        stream2 = conn.newStream(0)

        logger.info("Open safe console connection while an existing one is open")
        try:
            dom.openConsole(device, stream2, libvirt.VIR_DOMAIN_CONSOLE_SAFE)
        except libvirtError as e:
            if e.get_error_code() == libvirt.VIR_ERR_OPERATION_FAILED:
                logger.info("Opening failed - OK")
            else:
                raise e
        else:
            raise TestError("Opening of console succeeded although shoud fail")

        logger.info("Abort the existing stream")
        stream.abort()

        logger.info("Re-try connecting to the console")
        dom.openConsole(device, stream2, libvirt.VIR_DOMAIN_CONSOLE_SAFE)

        logger.info("Re-try forcibly on already open console")

        logger.info("Creating stream object")
        stream = conn.newStream(0)

        dom.openConsole(device, stream, libvirt.VIR_DOMAIN_CONSOLE_FORCE)

        logger.info("Clean up streams")
        stream.finish()

        try:
            stream2.finish()
        except libvirtError as e:
            if e.get_error_code() == libvirt.VIR_ERR_RPC and \
               e.get_error_domain() == libvirt.VIR_FROM_STREAMS:
                logger.info("Stream was aborted successfuly")
            else:
                raise e
        else:
            raise TestError("stream2 should be aborted after forced console connection")

    except libvirtError as e:
        logger.error("Libvirt call failed: " + str(e))
        ret = 1

    except TestError as e:
        logger.error("Test failed: " + str(e))
        ret = 1

    else:
        logger.info("All tests succeeded")
        ret = 0

    finally:
        logger.info("Closing hypervisor connection")
        logger.info("Done")

    return ret
