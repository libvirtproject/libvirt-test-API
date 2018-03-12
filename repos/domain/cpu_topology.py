#!/usr/bin/env python
# To test domain cpu topology

import os
import re
import sys
import time
from xml.dom import minidom

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('guestname',
                   'username',
                   'password',
                   'sockets',
                   'cores',
                   'threads',)
optional_params = {}


def check_domain_running(conn, guestname, logger):
    """check if the domain exists"""
    defined_guest_names = conn.listDefinedDomains()

    if guestname not in defined_guest_names:
        logger.error("%s doesn't exist or still in running" % guestname)
        return 1
    else:
        return 0


def add_cpu_xml(domobj, guestname, sockets, cores, threads, logger):
    """edit domain xml description and insert <cpu> element"""

    guestxml = domobj.XMLDesc(0)
    logger.debug('''original guest %s xml :\n%s''' % (guestname, guestxml))

    doc = minidom.parseString(guestxml)
    cpu = doc.createElement('cpu')
    topology = doc.createElement('topology')
    topology.setAttribute('sockets', sockets)
    topology.setAttribute('cores', cores)
    topology.setAttribute('threads', threads)
    cpu.appendChild(topology)

    vcpuval = int(sockets) * int(cores) * int(threads)
    newvcpu = doc.createElement('vcpu')
    newvcpuval = doc.createTextNode(str(vcpuval))
    newvcpu.appendChild(newvcpuval)
    oldvcpu = doc.getElementsByTagName('vcpu')[0]

    domain = doc.getElementsByTagName('domain')[0]
    domain.appendChild(cpu)
    domain.replaceChild(newvcpu, oldvcpu)

    return doc.toxml()


def guest_undefine(domobj, logger):
    """undefine original guest"""
    try:
        logger.info("undefine guest")
        domobj.undefine()
        logger.info("undefine the domain is successful")
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        logger.error("fail to undefine domain")
        return 1

    return 0


def guest_define(domobj, domxml, logger):
    """define new guest xml"""
    try:
        logger.info("define guest")
        conn = domobj._conn
        conn.defineXML(domxml)
        logger.info("success to define new domain xml description")
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        logger.error("fail to define domain")
        return 1

    return 0


def guest_start(domobj, guestname, logger):
    """start guest"""
    timeout = 600
    ip = ''
    mac = utils.get_dom_mac_addr(guestname)

    try:
        logger.info("start guest")
        domobj.create()
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        logger.error("fail to start domain")
        return 1

    while timeout:
        time.sleep(10)
        timeout -= 10

        ip = utils.mac_to_ip(mac, 180)

        if not ip:
            logger.info(str(timeout) + "s left")
        else:
            logger.info("vm %s power on successfully" % guestname)
            logger.info("the ip address of vm %s is %s" % (guestname, ip))
            break

    if timeout <= 0:
        logger.info("fail to power on vm %s" % guestname)
        return 1, ip

    return 0, ip


def cpu_topology_chk(ip, username, password,
                     sockets, cores, threads, logger):
    """login the guest, run lscpu command to check the result"""
    lscpu = "lscpu"
    # sleep for 5 seconds
    time.sleep(40)
    ret, output = utils.remote_exec_pexpect(ip, username, password, lscpu)
    logger.debug("lscpu:")
    logger.debug(output)
    if ret:
        logger.error("failed to run lscpu on guest OS")
        return 1

    int = 0
    actual_thread = actual_core = actual_socket = ''

    for item in output.split('\r'):
        if int == 5:
            actual_thread = item.split()[-1]
            logger.info("the actual thread in the guest is %s" % actual_thread)
        if int == 6:
            actual_core = item.split()[-1]
            logger.info("the actual core in the guest is %s" % actual_core)
        if int == 7:
            actual_socket = item.split()[-1]
            logger.info("the actual socket in the guest is %s" % actual_socket)

        int += 1

    if actual_thread == '' or actual_core == '' or actual_socket == '':
        logger.error("No data was retrieved")
        return 1

    if actual_thread == threads and actual_core == cores and actual_socket == sockets:
        return 0
    else:
        logger.error("The data doesn't match!!!")
        return 1


def cpu_topology(params):
    """ edit domain xml description according to the values
        and login to the guest to check the results
    """
    logger = params['logger']
    guestname = params['guestname']
    username = params['username']
    password = params['password']
    sockets = params['sockets']
    cores = params['cores']
    threads = params['threads']

    logger.info("guestname is %s" % guestname)
    logger.info("sockets is %s" % sockets)
    logger.info("cores is %s" % cores)
    logger.info("threads is %s" % threads)

    conn = sharedmod.libvirtobj['conn']

    if check_domain_running(conn, guestname, logger):
        return 1

    domobj = conn.lookupByName(guestname)
    domxml = add_cpu_xml(domobj, guestname, sockets, cores, threads, logger)

    if guest_undefine(domobj, logger):
        return 1

    if guest_define(domobj, domxml, logger):
        return 1

    ret, ip = guest_start(domobj, guestname, logger)
    if ret:
        return 1

    if cpu_topology_chk(ip, username, password,
                        sockets, cores, threads, logger):
        return 1

    return 0
