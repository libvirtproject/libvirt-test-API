#!/usr/bin/evn python

import libvirt

from libvirt import libvirtError
from src import sharedmod
from xml.dom import minidom
from utils import utils

required_params = ('usagetype', 'usageid')
optional_params = {}


def check_secret(secretobj, usagetype, usageid, logger):
    XMLFile = minidom.parse("/etc/libvirt/secrets/%s.xml" %
                            secretobj.UUIDString())
    if usagetype == 'volume':
        diskpath = (XMLFile.getElementsByTagName('volume')[0]).childNodes[0].data
    elif usagetype == 'tls':
        diskpath = (XMLFile.getElementsByTagName('name')[0]).childNodes[0].data

    logger.info("diskpath: %s" % diskpath)
    if diskpath != usageid:
        return 1

    return 0


def secret_lookup_by_usage(params):
    logger = params['logger']
    usagetype = params['usagetype']
    usageid = params['usageid']

    logger.info("usgae type: %s" % usagetype)
    logger.info("usage id: %s" % usageid)

    if usagetype == "volume":
        type = libvirt.VIR_SECRET_USAGE_TYPE_VOLUME
    elif usagetype == "tls":
        if utils.version_compare("libvirt-python", 2, 5, 0, logger):
            type = libvirt.VIR_SECRET_USAGE_TYPE_TLS
        else:
            logger.info("Current libvirt-python don't support this flag.")
            return 0
    elif usagetype == "ceph":
        type = libvirt.VIR_SECRET_USAGE_TYPE_CEPH
    elif usagetype == "iscsi":
        type = libvirt.VIR_SECRET_USAGE_TYPE_ISCSI
    elif usagetype == "none":
        type = libvirt.VIR_SECRET_USAGE_TYPE_NONE
    else:
        logger.error("Don't support type %s." % usagetype)
        return 1

    try:
        conn = sharedmod.libvirtobj['conn']
        secretobj = conn.secretLookupByUsage(type, usageid)

        if not check_secret(secretobj, usagetype, usageid, logger):
            logger.info("PASS: check secret successful.")
        else:
            logger.error("FAIL: check secret failed.")
            return 1

    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    return 0
