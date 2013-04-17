#!/usr/bin/env python
# test console interactions with stream event handler
# This test open console and add event handler, when libvirt and
# stream set callback at writeable event, interact with domain
# console and do echo tests. Timer event handler is set for each
# event callback and counting.

import libvirt
import os
import time
import re

from libvirt import libvirtError

from utils import utils

count = 0
change = 0

required_params = ('guestname',)
optional_params = {}


def check_domain_running(conn, guestname, logger):
    """ check if the domain exists, may or may not be active """
    guest_names = []
    ids = conn.listDomainsID()
    for id in ids:
        obj = conn.lookupByID(id)
        guest_names.append(obj.name())

    if guestname not in guest_names:
        logger.error("%s doesn't exist or not running" % guestname)
        return 1
    else:
        return 0

def stdio_callback(watch, fd, events, opaque):
    stream = opaque[0]
    logger = opaque[1]
    logger.info("console event value is: %s" % events)
    if events == 1:
        readbuf = "Libvirt-test-API"
        stream.send(readbuf)
        logger.info("send %d bytes from stdio to stream" % len(readbuf))
    elif events == 2:
        received_data = stream.recv(1024)
        logger.info("write %d bytes from stream to stdio: %s" %
                    (len(str(received_data)), received_data))

def stream_callback(stream, events, opaque):
    global count
    logger = opaque
    logger.info("stream event value is: %s" % events)
    if events == 1:
        try:
            received_data = stream.recv(1024)
        except:
            return
        logger.info("write from stream to stdio: \n %s" % received_data)
    elif events == 2:
        if count == 1:
            readbuf = "root\r"
            stream.send(readbuf)
        elif count == 2:
            readbuf = "redhat\r"
            stream.send(readbuf)
        elif count == 6:
            readbuf = 'echo "Testing" \r'
            stream.send(readbuf)
        elif count == 7:
            readbuf = "exit\r"
            stream.send(readbuf)
        else:
            pass
        logger.info("some bytes in stream")

def timeout_callback(timer, opaque):
    logger = opaque
    logger.debug("timer callback fire: %s" % timer)
    global count
    count = count + 1
    logger.info("timeout count is: %s" % count)

def check_domain_kernel_line(guestname, username, password, logger):
    global change
    mac = utils.get_dom_mac_addr(guestname)
    logger.info("the mac address of vm %s is %s" % (guestname, mac))
    timeout = 300
    while timeout:
        ipaddr = utils.mac_to_ip(mac, 180)
        if not ipaddr:
            logger.info(str(timeout) + "s left")
            time.sleep(10)
            timeout -= 10
        else:
            logger.info("the ip address of vm %s is %s" % (guestname, ipaddr))
            break
    if timeout == 0:
        logger.error("vm %s fail to get ip address" % guestname)
        return 1

    cmd = "cat /boot/grub/grub.conf"
    ret, output = utils.remote_exec_pexpect(ipaddr, username, password, cmd)
    if ret:
        return 1

    if "WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!" in output:
        logger.error("failed to login to guest for ssh key changed")
        return 1

    logger.debug("guest boot grub conf is:\n%s" % output)
    out = re.split('\n', output)
    for i in range(len(out)):
        if re.search('^\tkernel', out[i]):
            if re.search('console=tty', out[i]):
                continue
            else:
                out[i] = out[i] + " console=ttyS0,115200"
                change = 1

    if change:
        str = "\n".join(out)
        logger.debug("Update guest kernel line to:\n%s" % str)
        cmd = "echo '%s' > /etc/grub.conf" % str
        ret, output = utils.remote_exec_pexpect(ipaddr, username, password,
                                                cmd)
        if ret:
            logger.error("fail to write /etc/grub.conf in guest")
            return 1
        logger.info("Updated guest kernel line")
    else:
        logger.info("No need to modify guest kernel line")

    return 0

def console_callback(params):
    """ open console of a domain, add event and timeout handler.
        update event and timer handler, do console interaction.
    """
    global count
    global change
    logger = params['logger']
    guestname = params['guestname']
    username = 'root'
    password = 'redhat'
    logger.info("the guestname is %s" % guestname)

    try:
        conn = libvirt.open(None)
        domobj = conn.lookupByName(guestname)

        libvirt.virEventRegisterDefaultImpl()

        if check_domain_running(conn, guestname, logger):
            return 1

        ret = check_domain_kernel_line(guestname, username, password, logger)
        if ret:
            logger.error("Fail to check domain kernel line")
            return 1
        if change:
            logger.info("Now reboot the domain")
            domobj.shutdown()
            time.sleep(60)
            domobj.create()
            time.sleep(180)

        timeout = 500
        logger.info("Now add libvirt timeout handler with timeout as: %sms" %
                    timeout)
        timer = libvirt.virEventAddTimeout(int(timeout), timeout_callback,
                                           logger)
        logger.info("Added timeout handler with a new timer: %s" % timer)

        logger.info("Open console to a new stream")
        stream = conn.newStream(0)
        domobj.openConsole(None, stream, libvirt.VIR_DOMAIN_CONSOLE_FORCE)

        logger.info("Add libvirt event handler on VIR_EVENT_HANDLE_READABLE")
        watch = libvirt.virEventAddHandle(0, libvirt.VIR_EVENT_HANDLE_READABLE,
                                          stdio_callback, (stream, logger))
        logger.info("Handler added, the watch id is: %s" % watch)

        logger.info("Add stream event callback handler")
        stream.eventAddCallback(libvirt.VIR_STREAM_EVENT_READABLE,
                                stream_callback, logger)

        while True:
            libvirt.virEventRunDefaultImpl()
            if count > 3:
                break

        logger.info("Now update stream event handler on both read/write")
        stream.eventUpdateCallback(libvirt.VIR_STREAM_EVENT_WRITABLE|
                                   libvirt.VIR_STREAM_EVENT_READABLE)
        logger.info("Now update libvirt event handler on both read/write")
        libvirt.virEventUpdateHandle(watch, libvirt.VIR_EVENT_HANDLE_WRITABLE|
                                     libvirt.VIR_EVENT_HANDLE_READABLE)
        logger.info("Now update libvirt timeout value as: 15ms")
        libvirt.virEventUpdateTimeout(timer, 15)

        count = 0
        while True:
            libvirt.virEventRunDefaultImpl()
            time.sleep(2)
            if count > 7:
                break

        libvirt.virEventRemoveTimeout(timer)
        stream.eventRemoveCallback()
        libvirt.virEventRemoveHandle(watch)
    except libvirtError, e:
        logger.error("Libvirt call failed: " + str(e))
        return 1

    logger.info("Testing succeeded")
    return 0
