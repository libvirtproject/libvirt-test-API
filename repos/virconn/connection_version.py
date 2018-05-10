#!/usr/bin/env python
# test libvirt connection version

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ()
optional_params = {'uri': None}


def produce_ver_num(major, minor, release):
    """produce the version number
    """
    num = major * 1000000 + minor * 1000 + release
    return num


def check_libvirt_ver_num(conn, logger):
    """check libvirt version number
    """
    libvirt_version = utils.get_libvirt_version()
    logger.info("libvirt version is %s" % libvirt_version)
    ver = libvirt_version.split('-')[1]
    x = int(ver.split('.')[0])
    y = int(ver.split('.')[1])
    z = int(ver.split('.')[2])
    libvirt_ver_num = produce_ver_num(x, y, z)

    conn_lib_ver = conn.getLibVersion()
    logger.info("get libvirt version from connection: %s" % conn_lib_ver)

    if conn_lib_ver != libvirt_ver_num:
        logger.error("libvirt version is wrong, should be %s" %
                     libvirt_ver_num)
        return False
    return True


def check_hypervisor_ver_num(conn, logger):
    """check hypervisor version number
    """
    # TODO: modify utils.get_hypervisor, support lxc, openvz, and so on
    conn_type = conn.getType()
    logger.info("connection's type is %s" % conn_type)

    if str.lower(conn_type) == 'qemu':
        cmds = "rpm -q qemu-kvm"
        ver_num_pos = 2
        (status, output) = utils.exec_cmd(cmds, shell=True)
        if status != 0:
            cmds = "rpm -q qemu-kvm-rhev"
            ver_num_pos = 3
            (status, output) = utils.exec_cmd(cmds, shell=True)
            if status != 0:
                logger.error("Could not be aware of qemu")
                return False
        hyper_version = utils.decode_to_text(output[0])
        ver = hyper_version.split('-')[ver_num_pos]
        x = int(ver.split('.')[0])
        y = int(ver.split('.')[1])
        z = int(ver.split('.')[2])
    elif str.lower(conn_type) == 'lxc':
        cmds = "uname -r"
        (status, output) = utils.exec_cmd(cmds, shell=True)
        if status != 0:
            logger.error("Exec_cmd failed: %s" % cmds)
            return False
        hyper_version = utils.decode_to_text(output[0])
        ver = hyper_version.split('-')[0]
        x = int(ver.split('.')[0])
        y = int(ver.split('.')[1])
        z = int(ver.split('.')[2])
    else:
        logger.error("This hypervisor %s is unsupported currently" % conn_type)
        return False

    hyper_ver_num = produce_ver_num(x, y, z)

    conn_hyper_ver = conn.getVersion()
    logger.info("get hypervisor version from connection: %s" % conn_hyper_ver)
    if conn_hyper_ver != hyper_ver_num:
        logger.error("libvirt version is wrong, should be %s" % hyper_ver_num)
        return False
    return True


def connection_version(params):
    """test libvirt connection version
    """
    logger = params['logger']
    uri = params.get("uri", None)

    try:
        # get connection firstly.
        # If uri is not specified, use conn from sharedmod
        if 'uri' in params:
            conn = libvirt.open(uri)
        else:
            conn = sharedmod.libvirtobj['conn']

        # check libvirt version number
        if not check_libvirt_ver_num(conn, logger):
            logger.error("Failed to check libvirt version number")
            return 1

        # check hypervisor version number
        if not check_hypervisor_ver_num(conn, logger):
            logger.error("Failed to check hypervisor version number")
            return 1

    except libvirtError as e:
        logger.error("API error message: %s, error code is %s" %
                     e.get_error_message())
        logger.error("start failed")
        return 1

    return 0
