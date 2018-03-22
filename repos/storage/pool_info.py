#!/usr/bin/env python
#get info from a storage pool

from lxml import etree as ET
from libvirt import libvirtError
from src import sharedmod

required_params = ('poolname',)
optional_params = {}

NAME_LIST = ['state', 'capacity', 'allocation', 'available']


def get_elem(pool_xml, elem_list, state):
    """get value of pool state, capacity, allocation, available from XMLDesc"""
    tree = ET.XML(pool_xml)
    for i in range(len(NAME_LIST)):
        for elem in tree.iter(tag=NAME_LIST[i]):
            if i > 0:
                elem_list[i] = int(elem.text)
            break
    elem_list[0] = state


def check_info(elem_list, info_list):
    """compare whether is equal between elem_list and info_list"""
    for i in range(len(NAME_LIST)):
        if elem_list[i] != info_list[i]:
            logger.error("%s is not as expected" % NAME_LIST[i])
            return 1
        logger.debug("%s value in xml is %d" % (NAME_LIST[i], elem_list[i]))
        logger.debug("%s value in pool-info is %d" % (NAME_LIST[i], info_list[i]))
    return 0


def pool_info(params):
    """get info from a storage pool"""
    global logger
    logger = params['logger']
    poolname = params['poolname']

    conn = sharedmod.libvirtobj['conn']
    poolobj = conn.storagePoolLookupByName(poolname)
    pool_xml = poolobj.XMLDesc(0)

    elem_list = ['', '', '', '']
    info_list = elem_list
    if poolobj.isActive():
        state = 2
    else:
        state = 0

    get_elem(pool_xml, elem_list, state)
    logger.info("pool elem_list from xml is: %s" % elem_list)

    try:
        info_list = poolobj.info()
        logger.info("pool info is: %s" % info_list)
        ret = check_info(elem_list, info_list)
        if ret:
            return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1
    logger.info("PASS")
    return 0
