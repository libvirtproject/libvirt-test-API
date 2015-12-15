#!/usr/bin/evn python

import os
from libvirt import libvirtError
from src import sharedmod
from xml.dom import minidom

required_params = ('secretUUID',)
optional_params = {}


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
    conn = sharedmod.libvirtobj['conn']

    secretobj = conn.secretLookupByUUIDString(secretUUID)
    ephemeral = minidom.parseString(secretobj.XMLDesc(0)).\
        getElementsByTagName('secret')[0].getAttribute('ephemeral')
    diskpath = minidom.parseString(secretobj.XMLDesc(0)).\
        getElementsByTagName('volume')[0].childNodes[0].data
    try:
        secretobj.undefine()
        if check_undefineSecret(ephemeral, secretUUID):
            logger.info("undefine the secret %s is successful" % secretUUID)
            logger.info("remove the related volume %s" % diskpath)
            os.remove(diskpath)
        else:
            logger.error("fail to check secret undefine")
            return 1

    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
