#!/usr/bin/env python
# test libvirt free pages

import os
import resource

from libvirt import libvirtError

from src import sharedmod

required_params = ('cellid', 'pagesize',)
optional_params = {}

HUGEPAGE_PATH = '/sys/devices/system/node/node%s/hugepages/hugepages-%skB/free_hugepages'


def parse_unit(pagesz):
    """ parse a integer value, its unit is KiB
    """
    val = int(pagesz[0:len(pagesz) - 1])
    unit = pagesz[-1]
    if unit == 'K':
        unit = 1
    elif unit == 'M':
        unit = 1024
    elif unit == 'G':
        unit = 1024 * 1024
    else:
        return None

    return val * unit


def parse_page_list(pagesize):
    """ parse page size
    """
    if pagesize is None:
        return None

    l = list()
    for ps in pagesize.split(','):
        ps = ps.strip().upper()
        val = parse_unit(ps)
        if val is None:
            return None
        l.append(val)
    return l


def check_free_pages(page_list, cell_id, free_page, logger):
    """ check page size
    """
    for ps in page_list:
        # if pagesize is equal to system pagesize, since it is hard to
        # calculate, so we just pass it
        if resource.getpagesize() / 1024 == ps:
            logger.info("skip to check default %sKB-page" % ps)
            continue

        sysfs_path = HUGEPAGE_PATH % (cell_id, ps)
        if not os.access(sysfs_path, os.R_OK):
            logger.error("could not find %s" % sysfs_path)
            return False
        f = open(sysfs_path)
        fp = int(f.read())
        f.close()
        if not fp == free_page[0][ps]:
            logger.error("Free %sKB page checking failed" % ps)
            return False
        logger.info("Free %sKB page: %s" % (ps, fp))

    return True


def free_pages(params):
    """ test libvirt free pages
    """
    logger = params['logger']
    cell_id = int(params['cellid'])

    conn = sharedmod.libvirtobj['conn']

    page_list = parse_page_list(params['pagesize'])
    if page_list is None:
        logger.error("pagesize could not be recognized")
        return 1

    try:
        free_page = conn.getFreePages(page_list, cell_id, 1)

        if check_free_pages(page_list, cell_id, free_page, logger):
            logger.info("Success to check free page")
        else:
            logger.error("Failed to check free page")
            return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s" %
                     e.message)
        return 1
    return 0
