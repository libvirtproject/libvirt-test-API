#!/usr/bin/env python
# Test finding storage pool source of 'logical' type

from xml.dom import minidom
from libvirt import libvirtError
from src import sharedmod
from utils import utils

required_params = ('sourcepath',)
optional_params = {'xml': 'xmls/logical_pool.xml',
                   }


def check_pool_sources(xmlstr):
    """check the logical sources with command:
       pvs --noheadings -o pv_name,vg_name
    """
    source_val = {}
    source_cmp = {}

    doc = minidom.parseString(xmlstr)
    for diskTag in doc.getElementsByTagName("source"):
        device_element = diskTag.getElementsByTagName("device")[0]
        attr = device_element.getAttributeNode('path')
        path_val = attr.nodeValue

        name_element = diskTag.getElementsByTagName("name")[0]
        textnode = name_element.childNodes[0]
        name_val = textnode.data

        source_val.update({path_val: name_val, })

    logger.debug("pool source info dict is: %s" % source_val)

    cmd = "pvs --noheadings -o pv_name,vg_name | awk -F' ' '{print $1}'"
    ret, path_list = utils.exec_cmd(cmd, shell=True)

    cmd = "pvs --noheadings -o pv_name,vg_name | awk -F' ' '{print $2}'"
    ret, name_list = utils.exec_cmd(cmd, shell=True)

    for i in range(len(path_list)):
        source_cmp.update({path_list[i]: name_list[i]})

    logger.debug("pvs command output dict is: %s" % source_cmp)

    if source_val == source_cmp:
        logger.info("source dict match with pvs command output")
        return 0
    else:
        logger.error("source dict did not match with pvs command output")
        return 1


def find_logical_pool_sources(params):
    """Find logical type storage pool sources from xml"""
    global logger
    logger = params['logger']
    sourcepath = params['sourcepath']
    xmlstr = params['xml']

    conn = sharedmod.libvirtobj['conn']
    try:

        logger.debug("storage source spec xml:\n%s" % xmlstr)

        logger.info("find pool sources of logical type")
        source_xml = conn.findStoragePoolSources('logical', xmlstr, 0)
        logger.info("pool sources xml description is:\n %s" % source_xml)

        ret = check_pool_sources(source_xml)
        if ret:
            logger.error("pool sources check failed")
            return 1
        else:
            logger.info("pool sources check succeed")

    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    return 0
