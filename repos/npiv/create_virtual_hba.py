#!/usr/bin/env python
# To test vHBA creating with npiv.

import re
import time

from libvirt import libvirtError
from utils import utils
from utils import process
from src import sharedmod

required_params = ('wwpn', 'wwnn',)
optional_params = {'xml': 'xmls/virtual_hba.xml',
                   }


def check_nodedev_create(wwpn, device_name):
    """Check if the node device vHBA was created. Can search created
       vport name in all FC list, to see if it exists.
    """
    cmd = "ls -1 -d /sys/class/*_host/host*/* | grep port_name"
    ret = process.run(cmd, shell=True, ignore_status=True)
    pname_list = ret.stdout
    for pname in pname_list.split("\n"):
        portid = open(pname).read()[2:].strip('\n')
        if wwpn == portid:
            logger.info("created virtual port name is %s" % portid)
            logger.info("The vHBA '%s' was created." % device_name)
            return True

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


def check_port_state(scsi_name, logger):
    cmd = "cat /sys/class/fc_host/%s/port_state" % scsi_name
    status, out = utils.exec_cmd(cmd, shell=True)
    if status:
        logger.error("Get port state failed: %s" % scsi_name)
        return 1
    logger.info("%s state is %s" % (scsi_name, out))
    if out[0] == "Online":
        return 0
    else:
        return 1


def create_virtual_hba(params):
    """Create a vHBA with NPIV supported FC HBA."""
    global logger
    logger = params['logger']
    wwpn_node = params['wwpn']
    wwnn_node = params['wwnn']
    xmlstr = params['xml']

    conn = sharedmod.libvirtobj['conn']

    scsi_list = conn.listDevices('scsi_host', 0)

    device_parent = ''
    for fc_name in scsi_list:
        nodedev = conn.nodeDeviceLookupByName(fc_name)
        fc_xml = nodedev.XMLDesc(0)
        fc_cap = re.search('vport_ops', fc_xml)
        if fc_cap:
            scsi_name = fc_name.split('_')
            if check_port_state(scsi_name[1], logger):
                continue

            device_parent = fc_name
            xmlstr = xmlstr.replace('PARENT', device_parent)
            xmlstr = xmlstr.replace('WWNN', wwnn_node)
            xmlstr = xmlstr.replace('WWPN', wwpn_node)
            logger.info("NPIV support on '%s'" % fc_name)
            break

    logger.info("node device xml:\n%s" % xmlstr)

    try:
        logger.info("creating a virtual HBA ...")
        nodedev_obj = conn.nodeDeviceCreateXML(xmlstr, 0)
        time.sleep(3)
        dev_name = nodedev_obj.name()
        if check_nodedev_create(wwpn_node, dev_name) and \
                check_nodedev_parent(nodedev_obj, device_parent, dev_name):
            logger.info("the virtual HBA '%s' was created successfully"
                        % dev_name)
            return 0
        else:
            logger.error("fail to create the virtual HBA '%s'"
                         % dev_name)
            return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    return 0
