#!/usr/bin/env python

from libvirt import libvirtError
from utils import utils

from src import sharedmod

required_params = ()
optional_params = {}

NWFILTER_LIST_API_DIR = "ls /etc/libvirt/nwfilter"


def get_nwfilterlist_dir():
    """ Get the nwfilter list from dir """

    (status, output) = utils.exec_cmd(NWFILTER_LIST_API_DIR, shell=True)
    logger.info("Execute command:" + NWFILTER_LIST_API_DIR)
    nwfilter_list_api_dir = []
    if status:
        logger.error("Executing " + NWFILTER_LIST_API_DIR + " failed")
        logger.error(output)
        return False
    else:
        for i in range(len(output)):
            nwfilter_list_api_dir.append(output[i][:-4])
        logger.info("Get nwfilters name list under dir: %s"
                    % nwfilter_list_api_dir)
        nwfilter_list_api_dir.sort()
        return nwfilter_list_api_dir


def nwfilter_list(params):
    """ List all of the available network filters."""
    global logger
    logger = params['logger']
    conn = sharedmod.libvirtobj['conn']

    try:
        # Get the nwfilter name list from API """
        nwfilter_namelist_api = conn.listNWFilters()
        nwfilter_namelist_api.sort()

        # Get the nwfilter object list
        nwfilter_list_api = conn.listAllNWFilters(0)
        logger.info("The connection URI %s" %
                    nwfilter_list_api[0].connect().getURI())

        # Get the number of nwfilters from API
        nwfilter_num = conn.numOfNWFilters()

        nwfilter_list_dir = get_nwfilterlist_dir()
        if nwfilter_num == len(nwfilter_list_api) and \
                len(nwfilter_list_api) == len(nwfilter_list_dir) and \
                cmp(nwfilter_namelist_api, nwfilter_list_dir) == 0:
            logger.info("The number of available network filters is %s" %
                        nwfilter_num)
        else:
            logger.error("Failed to get the nwfilters list")
            return 1

        for nwfilter_item in nwfilter_list_api:
            if nwfilter_item.name()in nwfilter_list_dir and \
                    nwfilter_item.name()in nwfilter_namelist_api:
                logger.info("The name is %s" % nwfilter_item.name())
            else:
                logger.error("Failed to get nwfilter's name.")
                return 1
            if cmp(str(nwfilter_item.UUID()), nwfilter_item.UUIDString()):
                logger.info("The UUID is %s" % nwfilter_item.UUIDString())
            else:
                logger.error("Failed to get nwfilter's uuid.")
                return 1

    except libvirtError as e:
        logger.error("API error message: %s" % e.get_error_message())
        return 1

    return 0
