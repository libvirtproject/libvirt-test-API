#!/usr/bin/env python
# test console interactions
# This test sends contents of file 'input' to the guest's console
# and reads from the console the reply and compares it to 'expect' or
# writes the output to file 'output'

import libvirt
import signal
import os

from libvirt import libvirtError
from exception import TestError

from src import sharedmod

required_params = ('guestname',)
optional_params = {'device': 'serial0',
                   'timeout': 5,
                   'input': None,
                   'output': None,
                   'expect': None
                   }


def alarm_handler(signum, frame):
    raise TestError("Timed out while waiting for console")


def console_io(params):
    """Attach to console"""
    logger = params['logger']
    guest = params['guestname']
    device = params.get('device', 'serial0')
    infile = params.get('input', None)
    outfile = params.get('output', None)
    expect = params.get('expect', None)
    timeout = params.get('timeout', 5)

    # store the old signal handler
    oldhandler = signal.getsignal(signal.SIGALRM)

    try:
        conn = sharedmod.libvirtobj['conn']
        dom = conn.lookupByName(guest)
        if not dom.isActive():
            raise TestError("Guest '%s' not active" % guest)

        logger.info("Creating stream object")
        stream = conn.newStream(0)

        logger.info("Open a new console connection")
        dom.openConsole(device, stream, libvirt.VIR_DOMAIN_CONSOLE_FORCE)

        if infile is not None:
            try:
                f = open(infile, 'r')
                instr = f.read()
                f.close()
            except Exception as e:
                raise TestError("Can't read input file '%s': %s" % (infile, str(e)))

            logger.info(
                "Sending %d bytes of contents of file '%s' to console '%s'" %
                (len(instr), infile, device))
            stream.send(instr)

        if expect is not None or outfile is not None:
            logger.info("Recieving data from console device. Timeout %d seconds." % timeout)

            # register a new signal handler
            logger.info("Registering custom SIGALRM handler")
            signal.signal(signal.SIGALRM, alarm_handler)
            signal.alarm(timeout)

            reply = ""
            try:
                while True:
                    recv = stream.recv(1024)
                    reply += recv
            except TestError:
                pass

            logger.info("Recieved %d bytes." % len(reply))

            if outfile is not None:
                try:
                    f = open(outfile, 'w')
                    f.write(reply)
                    f.close()
                except Exception as e:
                    raise TestError(
                        "Can't write output to file '%s': %s" % (outfile, str(e)))

            if expect is not None:
                try:
                    f = open(expect, 'r')
                    expectstr = f.read()
                    f.close()
                except Exception as e:
                    raise TestError(
                        "Can't read expected output file '%s': '%s'" % (expect, str(e)))

                if reply.startswith(expectstr):
                    logger.info("Recieved expected output from the host")
                else:
                    raise TestError(
                        "Reply from the guest doesn't match with expected reply")

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
        logger.info("Restoring signal handler")
        signal.signal(signal.SIGALRM, oldhandler)
        logger.info("Closing hypervisor connection")
        try:
            stream.abort()
        except:
            pass

        logger.info("Done")

    return ret
