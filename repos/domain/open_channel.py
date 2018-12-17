#!/usr/bin/env python
# Test openChannel
# Accept flag channel as a number presents which channel to use
# When no channel is given, will perform test on first avaliable channel

import libvirt
import time

from libvirt import libvirtError

from src import sharedmod

required_params = ('guestname',)
optional_params = {'channel': None}


def open_channel(params):
    """ open channel of a domain, check if it's opened
        successfully and writable or readable
    """

    logger = params['logger']
    guestname = params['guestname']
    logger.info("the guestname is %s" % guestname)
    counter = {'read': 0, 'write': 0}

    def channel_callback(stream, events, opaque):
        logger = opaque
        if events == libvirt.VIR_EVENT_HANDLE_READABLE:
            logger.info("Channel is readable")
            try:
                received_data = stream.recv(1024)
            except libvirtError as e:
                logger.error("Stream recv error: %s" % str(e))
                return
            counter['read'] = counter['read'] + 1
        elif events == libvirt.VIR_EVENT_HANDLE_WRITABLE:
            logger.info("Channel is writable")
            try:
                stream.send("\r")
            except libvirtError as e:
                logger.error("Stream send error: %s" % str(e))
                return
            counter['write'] = counter['write'] + 1

    try:
        conn = sharedmod.libvirtobj['conn']
        domobj = conn.lookupByName(guestname)

        libvirt.virEventRegisterDefaultImpl()

        logger.info("Open console to a new stream")
        stream = conn.newStream(libvirt.VIR_STREAM_NONBLOCK)
        channel = params.get('channel', None)

        logger.info("Openning %s" % (channel or "first avaliable channel"))
        domobj.openChannel(channel, stream, libvirt.VIR_DOMAIN_CHANNEL_FORCE)

        logger.info("Add stream event callback handler")
        stream.eventAddCallback(libvirt.VIR_STREAM_EVENT_READABLE |
                                libvirt.VIR_STREAM_EVENT_READABLE,
                                channel_callback, logger)

        stream.eventUpdateCallback(libvirt.VIR_STREAM_EVENT_WRITABLE |
                                   libvirt.VIR_STREAM_EVENT_READABLE)

        count = 0
        while True:
            libvirt.virEventRunDefaultImpl()
            time.sleep(1)
            count = count + 1
            if count > 5:
                break

        logger.info("Performed %d times of write, %d times of read."
                    % (counter['write'], counter['read']))

        if counter['write'] + counter['read'] == 0:
            logger.error("Interface is not readable/writable")
            return

        if channel:
            success = False
            try:
                logger.info("Trying to open an unavaliable channel")
                domobj.openChannel(channel, stream)
            except libvirtError as e:
                logger.info("Failed as expected")
                success = True

            if success is False:
                logger.err("Opened an unavaliable channel")
                return 1

        stream.eventRemoveCallback()
        stream.finish()

    except libvirtError as e:
        logger.error("Libvirt call failed: " + str(e))
        return 1

    logger.info("Testing succeeded")
    return 0
