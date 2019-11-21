#!/usr/bin/env python

import libvirt
import lxml
import lxml.etree

from libvirt import libvirtError
from src import sharedmod

required_params = ()
optional_params = {'uri': None, 'flags': None}

HOST_HUGEPAGE = '/sys/devices/system/node/node%d/hugepages/hugepages-%dkB/nr_hugepages'


def get_host_pagesize(conn):
    ret = []
    tree = lxml.etree.fromstring(conn.getCapabilities())

    set = tree.xpath("/capabilities/host/cpu/pages")
    for n in set:
        ret.append(int(n.attrib['size']))

    return ret


def get_host_pagecount(pagesize):
    try:
        return int(open(HOST_HUGEPAGE % (0, pagesize)).read())
    except IOError:
        return -1


def connection_allocPages(params):
    """
       test API for allocPages in class virConnect
    """
    logger = params['logger']
    uri = params.get("uri", None)
    fail = 0

    if 'flags' in params:
        flags = params.get("flags", None)
        if flags == 'pageset':
            libvirt_flags = libvirt.VIR_NODE_ALLOC_PAGES_SET
        else:
            logger.error("Unknown flags name: %s" % flags)
            return 1
    else:
        libvirt_flags = 0

    try:
        if 'uri' in params:
            conn = libvirt.open(uri)
        else:
            conn = sharedmod.libvirtobj['conn']
        logger.info("get connection to libvirtd")
        list1 = get_host_pagesize(conn)

    except libvirtError as e:
        logger.error("API error message: %s" % e.get_error_message())
        return 1

    for i in list1:
        logger.info("test hugepage size %d" % i)

        if get_host_pagecount(i) == -1:
            logger.info("Skip system page size %d" % i)
            continue

        try:
            cur_count = get_host_pagecount(i)
            if libvirt_flags == libvirt.VIR_NODE_ALLOC_PAGES_SET:
                conn.allocPages({i: cur_count + 1}, 0, 1, libvirt_flags)
            else:
                conn.allocPages({i: 1}, 0, 1, libvirt_flags)
            if get_host_pagecount(i) != cur_count + 1:
                logger.error("libvirt set a wrong page count to %dKiB hugepage" % i)
                fail = 1
        except libvirtError as e:
            if "Allocated only" in e.get_error_message():
                tmp_count = int(e.get_error_message().split()[-1])
                if tmp_count != get_host_pagecount(i):
                    logger.error("libvirt output %dKiB hugepage count is not right" % i)
                    fail = 1
            else:
                logger.error("API error message: %s" % e.get_error_message())
                return 1

    return fail
