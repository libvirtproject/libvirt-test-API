#!/usr/bin/env python
# To test vHBA destroying.

import commands
from libvirt import libvirtError
from src import sharedmod

required_params = ('wwpn',)
optional_params = {}


def destroy_virtual_hba(params):
    """Destroy the vHBA created before."""
    global logger
    logger = params['logger']
    wwpn_node = params['wwpn']

    conn = sharedmod.libvirtobj['conn']
    dev_name = ''
    pname_list = commands.getoutput("ls -1 -d /sys/class/*_host/host*/*"
                                    "| grep port_name")
    for pname in pname_list.split("\n"):
        portid = open(pname).read()[2:].strip('\n')
        if wwpn_node == portid:
            host_name = pname.split('/')
            dev_name = 'scsi_' + host_name[4]

    logger.info("destroying the virtual HBA %s" % dev_name)

    try:
        nodedev_obj = conn.nodeDeviceLookupByName(dev_name)
        nodedev_obj.destroy()

        scsi_list = conn.listDevices('scsi_host', 0)
        for fc_name in scsi_list:
            if fc_name == dev_name:
                logger.error("Fail to destroy the virtual HBA %s" % dev_name)
                return 1
        logger.info("Pass to destroy the virtual HBA %s" % dev_name)

    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("Error: fail to destroy %s virtual hba" % dev_name)
        return 1

    return 0
