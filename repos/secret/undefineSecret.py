#!/usr/bin/evn python

import os

from libvirt import libvirtError
from src import sharedmod
from xml.dom import minidom
from utils import utils

required_params = ('secretUUID',)
optional_params = {'usagetype': 'volume'}


def check_undefineSecret(ephemeral, secretUUID):
    """Check undefine secret result, if ephemeral is no, the secret xml will
       not exist under /etc/libvirt/secrets/ after undefine action;
       if ephemeral is yes, the secret UUID will not exist in the secret list.
    """
    path = "/etc/libvirt/secrets/%s.xml" % secretUUID

    if (ephemeral == 'no') and (not os.path.exists(path)):
        return 1
    elif (ephemeral == 'yes') and (secretUUID not in conn.listSecrets()):
        return 1
    else:
        return 0

    return 1


def undefineSecret(params):
    """Undefine a secret"""
    global conn
    logger = params['logger']
    secretUUID = params['secretUUID']
    usagetype = params.get('usagetype', 'volume')

    conn = sharedmod.libvirtobj['conn']

    secretobj = conn.secretLookupByUUIDString(secretUUID)
    ephemeral = minidom.parseString(secretobj.XMLDesc(0)).\
        getElementsByTagName('secret')[0].getAttribute('ephemeral')
    if usagetype == "volume":
        diskpath = minidom.parseString(secretobj.XMLDesc(0)).\
            getElementsByTagName('volume')[0].childNodes[0].data
    elif usagetype == "vtpm":
        if not utils.version_compare("libvirt-python", 5, 6, 0, logger):
            logger.info("Current libvirt-python don't support 'vtpm'.")
            return 0
    try:
        secretobj.undefine()
        if check_undefineSecret(ephemeral, secretUUID):
            logger.info("undefine the secret %s is successful" % secretUUID)
            if usagetype == "volume":
                logger.info("remove the related volume %s" % diskpath)
                os.remove(diskpath)
        else:
            logger.error("fail to check secret undefine")
            return 1

    except libvirtError as err:
        logger.error("API error message: %s, error code is %s"
                     % (err.get_error_message(), err.get_error_code()))
        return 1

    return 0
