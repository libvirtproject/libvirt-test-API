#!/usr/bin/python

from libvirt import libvirtError

from src import sharedmod
from utils import utils

GET_NATIVE_CONFIG = "grep %s /var/log/libvirt/qemu/%s.log | tail -1"
SPLIT_STR = " -"

required_params = ('nativeformat', 'guestname')
optional_params = {}

def check_domxml_to_native(nativeconfig, guestname):
    """Check the result form API domainXMLFromNative,
       compare the result with the native config in
       /var/log/libvirt/qemu/$vm.log, and remove vnc
       port and netdev part before compare.
    """
    (status, output) = utils.exec_cmd(GET_NATIVE_CONFIG % \
                    (guestname, guestname), shell=True)
    if status:
        logger.error("Fail to get native config of domain %s" % guestname)
        return 1
    nativeconLog = output[0]

    nativeconLog = nativeconLog.split(SPLIT_STR)
    nativeconfig = nativeconfig.split(SPLIT_STR)

    # Revmoe the netdev part because mac is always be zero,
    #
    # Remove vnc port because the port will change if there are
    # other vnc guests on the host, and this is not a problem for
    # this API.

    #convert native config from log
    temp = nativeconLog[:]
    for item in temp:
        if 'netdev' in item:
            nativeconLog.remove(item)

        if "vnc" in item:
            ret = nativeconLog.index(item)
            nativeconLog.remove(item)
            item = item.split(":")[0]
            nativeconLog.insert(ret, item)

        if "S" == item:
            nativeconLog.remove(item)

    #convert native config from API
    temp = nativeconfig[:]
    for item in temp:
        if 'netdev' in item:
            nativeconfig.remove(item)

        if "vnc" in item:
            ret = nativeconfig.index(item)
            nativeconfig.remove(item)
            item = item.split(":")[0]
            nativeconfig.insert(ret, item)

        if "S" == item:
            nativeconLog.remove(item)

    nativeconLog = SPLIT_STR.join(nativeconLog)
    nativeconfig = SPLIT_STR.join(nativeconfig)

    logger.debug("Native config from domain log is:  %s" % nativeconLog)
    logger.info("Native config from API is :  %s" % nativeconfig)
    if cmp(nativeconLog, nativeconfig) == 0:
        logger.info("native config from API can match the config form log")
        return 0
    else:
        logger.error("native config from API is not same with log")
        return 1

    return 0

def domxml_to_native(params):
    """Test API domainXMLFromNative to convert
       a native configuration to a domain XML
       configuration
    """
    global logger
    logger = params['logger']
    conn = sharedmod.libvirtobj['conn']
    nativeformat = params['nativeformat']
    guestname = params['guestname']
    guest = conn.lookupByName(guestname)
    xmlstr = guest.XMLDesc()

    try:
        nativeconfig = conn.domainXMLToNative(nativeformat, xmlstr, 0)
        if check_domxml_to_native(nativeconfig, guestname):
            logger.error("The domain xml get from API domainXMLFromNative is \
                         not right")
            return 1
        else:
            logger.info("The domain xml get from API domainXMLFromNative \
                        successfully!")
            return 0
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s" \
                     % (e.message, e.get_error_code()))
        return 1

    return 0
