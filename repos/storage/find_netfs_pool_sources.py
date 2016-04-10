#!/usr/bin/env python
# Test finding storage pool source of 'netfs' type

from xml.dom import minidom
from libvirt import libvirtError
from src import sharedmod
from utils import utils

required_params = ('sourcehost',)
optional_params = {'xml': 'xmls/netfs_pool_source.xml',
                   }


def check_pool_sources(host, xmlstr):
    """check the netfs sources with command:
       showmount --no-headers -e HOSTNAME
    """
    source_val = []

    doc = minidom.parseString(xmlstr)
    for diskTag in doc.getElementsByTagName("source"):
        device_element = diskTag.getElementsByTagName("dir")[0]
        attr = device_element.getAttributeNode('path')
        path_val = attr.nodeValue

        source_val.append(path_val)

    logger.debug("pool source info list is: %s" % source_val)

    cmd = "showmount --no-headers -e %s | awk -F' ' '{print $1}'" % host
    ret, path_list = utils.exec_cmd(cmd, shell=True)

    logger.debug("showmount command output list is: %s" % path_list)

    if source_val == path_list:
        logger.info("source list matched with showmount command output")
        return 0
    else:
        logger.error("source list did not match with showmount command output")
        return 1


def find_netfs_pool_sources(params):
    """Find netfs type storage pool sources from xml"""
    global logger
    logger = params['logger']
    sourcehost = params['sourcehost']
    xmlstr = params['xml']

    conn = sharedmod.libvirtobj['conn']
    try:

        logger.debug("storage source spec xml:\n%s" % xmlstr)

        logger.info("find pool sources of netfs type")
        source_xml = conn.findStoragePoolSources('netfs', xmlstr, 0)
        logger.info("pool sources xml description is:\n %s" % source_xml)

        ret = check_pool_sources(sourcehost, source_xml)
        if ret:
            logger.error("pool sources check failed")
            return 1
        else:
            logger.info("pool sources check succeed")

    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    return 0
