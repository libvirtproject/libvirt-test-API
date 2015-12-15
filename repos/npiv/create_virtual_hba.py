#!/usr/bin/env python
# To test vHBA creating with npiv.

import os
import sys
import re
import commands
import xml.dom.minidom

import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ('wwpn',)
optional_params = {'xml': 'xmls/virtual_hba.xml',
                   }


def check_nodedev_create(wwpn, device_name):
    """Check if the node device vHBA was created. Can search created
       vport name in all FC list, to see if it exists.
    """

    pname_list = commands.getoutput("ls -1 -d /sys/class/*_host/host*/*"
                                    " | grep port_name")
    for pname in pname_list.split("\n"):
        portid = open(pname).read()[2:].strip('\n')
        if wwpn == portid:
            logger.info("created virtual port name is %s" % portid)
            logger.info("The vHBA '%s' was created." % device_name)
            return True
        else:
            logger.info("No any virtual HBA was created")
            return False


def check_nodedev_parent(nodedev_obj, device_parent, device_name):
    """Check created vHBA if its parent is correct. It's a bug 593995."""

    current_parent = nodedev_obj.parent()
    if device_parent == current_parent:
        logger.info("The parent of node device '%s' is %s"
                    % (device_name, current_parent))
        return True
    else:
        logger.info("Refer to bug 593995. The parent of node device "
                    "'%s' is '%s'" % (device_name, current_parent))
        return False


def create_virtual_hba(params):
    """Create a vHBA with NPIV supported FC HBA."""
    global logger
    logger = params['logger']
    wwpn = params['wwpn']
    xmlstr = params['xml']

    conn = sharedmod.libvirtobj['conn']

    scsi_list = conn.listDevices('scsi_host', 0)

    device_parent = ''
    for fc_name in scsi_list:
        nodedev = conn.nodeDeviceLookupByName(fc_name)
        fc_xml = nodedev.XMLDesc(0)
        fc_cap = re.search('vport_ops', fc_xml)
        if fc_cap:
            device_parent = fc_name
            xmlstr = xmlstr.replace('PARENT', device_parent)
            doc = xml.dom.minidom.parseString(fc_xml)
            wwnn_node = doc.getElementsByTagName('wwnn')[0]
            xmlstr = xmlstr.replace('WWNN', wwnn_node.childNodes[0].nodeValue.encode('ascii', 'ignore'))
            logger.info("NPIV support on '%s'" % fc_name)
            break
        else:
            logger.info("No NPIV capabilities on '%s'" % fc_name)

    logger.debug("node device xml:\n%s" % xmlstr)
    return 0

    try:
        logger.info("creating a virtual HBA ...")
        nodedev_obj = conn.nodeDeviceCreateXML(xmlstr, 0)
        dev_name = nodedev_obj.name()

        if check_nodedev_create(wwpn, dev_name) and \
                check_nodedev_parent(nodedev_obj, device_parent, dev_name):
            logger.info("the virtual HBA '%s' was created successfully"
                        % dev_name)
            return 0
        else:
            logger.error("fail to create the virtual HBA '%s'"
                         % dev_name)
            return 1
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        logger.error("Error: fail to create %s virtual hba" % dev_name)
        return 1

    return 0
