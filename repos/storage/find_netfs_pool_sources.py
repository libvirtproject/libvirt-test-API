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
    source_val = {}
    format_type = ""
    path_nfs = []
    path_gluster = []
    doc = minidom.parseString(xmlstr)
    for diskTag in doc.getElementsByTagName("source"):
        path_val = diskTag.getElementsByTagName("dir")[0].getAttributeNode('path').nodeValue
        format_type = diskTag.getElementsByTagName("format")[0].getAttributeNode('type').nodeValue
        if format_type == "nfs":
            path_nfs.append(path_val)
        elif format_type == "glusterfs":
            path_gluster.append(path_val)
        else:
            logger.error("Need to check %s type." % format_type)
            return 1

    if len(path_nfs) > 0:
        source_val['nfs'] = path_nfs
    if len(path_gluster) > 0:
        source_val['glusterfs'] = path_gluster
    logger.debug("pool source info: %s" % source_val)

    nfs_path_list = []
    gluster_path_list = []
    for key,value in source_val.items():
        if key == "nfs":
            cmd = "showmount --no-headers -e %s | awk -F' ' '{print $1}'" % host
            ret, nfs_path_list = utils.exec_cmd(cmd, shell=True)
            logger.debug("showmount command output list is: %s" % nfs_path_list)
            if nfs_path_list != value:
                logger.error("nfs pool sources don't match.")
                return 1
        elif key == "glusterfs":
            cmd = "grep '%s' /etc/hosts" % host
            ret, host_ip = utils.exec_cmd(cmd, shell=True)
            logger.debug("glusterfs host ip: %s" % host_ip[0].split(' ')[0])
            cmd = "gluster volume list --remote-host=%s" % host_ip[0].split(' ')[0]
            ret, gluster_path_list = utils.exec_cmd(cmd, shell=True)
            logger.debug("gluster type: %s" % gluster_path_list)
            if gluster_path_list != value:
                logger.error("glusterfs pool sources don't match.")
                return 1
        else:
            logger.error("Need to check %s type." % format_type)
            return 1

    logger.info("pool sources list match.")
    return 0


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
