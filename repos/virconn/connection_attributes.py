#!/usr/bin/env python
# test libvirt connection attributes

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ()
optional_params = {'uri': None}


def check_conn_type(conn, logger):
    """check connection's type
    """
    logger.info("Test connection's type")
    uri_type = conn.getType()
    logger.info("The connection's type is %s" % uri_type)
    uri_str = conn.getURI()
    logger.info("The connection's URI is %s" % uri_str)
    # because remote:// is redirect to the default hypervisor URI
    if 'remote' in uri_str:
        logger.info("Ignore remote:// URI testing")
    else:
        if str.lower(uri_type) not in str.lower(uri_str):
            logger.error("The connection %s has wrong type: %s" %
                         (uri_str, uri_type))
            return False
    return True


def check_conn_hostname(conn, logger):
    """check connection's hostname
    """
    logger.info("Test connection's hostname")
    output = utils.get_local_hostname()
    conn_hostname = conn.getHostname()
    logger.info("The connection's hostname is %s" % conn_hostname)

    if not conn_hostname == output:
        logger.error("The connection's hostname(%s) wrong, should be %s" %
                     (conn_hostname, output))
        return False
    return True


def connection_attributes(params):
    """test libvirt connection attributes
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

        # test connection is Alive
        if not conn.isAlive():
            logger.error("The connection is not alive")
            return 1

        # test connection type
        if not check_conn_type(conn, logger):
            logger.error("Failed to check connection type")
            return 1

        # test hostname of the connection
        if not check_conn_hostname(conn, logger):
            logger.error("Failed to check connection hostname")
            return 1

        # test connection's sysinfo
        logger.info("Test connection's sysinfo")
        conn_sysinfo = conn.getSysinfo(0)
        logger.info("The connection's sysinfo is:\n %s" % conn_sysinfo)

        # test connection's capabilities
        logger.info("Test connection's capabilities")
        conn_caps = conn.getCapabilities()
        logger.info("The connection's capabilities is:\n %s" % conn_caps)

    except libvirtError as e:
        logger.error("API error message: %s, error code is %s" %
                     e.get_error_message())
        logger.error("start failed")
        return 1

    return 0
