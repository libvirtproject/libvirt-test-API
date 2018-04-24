#!/usr/bin/env python
# Test domain's openGraphics API

import time
import os
import socket
import select
import libvirt

try:
    import thread
except ImportError:
    import _thread as thread

from libvirt import libvirtError
from src import sharedmod

required_params = ('guestname',)
optional_params = {'flags': '', 'idx': 0}


def parse_flag(flag):
    """ parse flags
    """
    if flag == 'skipauth':
        return libvirt.VIR_DOMAIN_OPEN_GRAPHICS_SKIPAUTH
    if flag is None:
        return 0
    return -1


def open_graphics(params):
    """ test openGraphics API
        create a socket pair, bind one of them with openGraphics
        listen on another then send some data and wait for response
        to make sure the socket is useable
    """
    logger = params['logger']
    guestname = params['guestname']
    idx = int(params.get('idx', 0))
    flag = parse_flag(params.get('flags'))

    if flag == -1:
        logger.error("invalid flags for openGraphics: %s" % flag)
        return 1

    logger.info("the guestname is %s" % guestname)
    logger.info("the idx is %s" % idx)
    logger.info("the flags is %s" % flag)

    shared = {'timeout': 20, 'success': False}

    try:
        logger.info("Opening socket...")
        server, client = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)

        def ClientFunc():
            client.setblocking(0)
            logger.info("Client listening...")
            while shared['timeout'] > 0:
                try:
                    data = client.recv(1024)
                    if data:
                        logger.info("Got data: %s" % data)
                        shared['success'] = True
                        return
                except socket.error as e:
                    logger.info("No data yet: %s" % e)
                try:
                    # Send some data...
                    client.send('HELP\r')
                    client.send('help\r')
                    client.send('h\r')
                    client.send('?\r')
                    client.send('\r')
                    time.sleep(1)
                except socket.error as e:
                    logger.info("Socket closed by server")
                    shared['success'] = True
                    return

        conn = libvirt.open(None)
        domobj = conn.lookupByName(guestname)

        domobj.openGraphics(idx, server.fileno(), flag)
        thread.start_new_thread(ClientFunc, ())
        while shared['timeout'] > 0 and shared['success'] is False:
            shared['timeout'] = shared['timeout'] - 1
            time.sleep(1)

            if shared['timeout'] == 0:
                time.sleep(1)
                if shared['success'] is False:
                    logger.error('Socket not responding')
                    return 1

    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    return 0
