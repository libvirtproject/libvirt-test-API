#!/usr/bin/env python

import libvirt
from libvirt import libvirtError
from src import sharedmod
from xml.dom import minidom

required_params = ('flag',)
optional_params = {}


def check_secretList(flags, secretobjs, conn):
    """check the secret list result
    """
    if (flags == 'none') and (len(secretobjs) == conn.numOfSecrets()):
        return 0
    elif flags == 'ephemeral':
        for i in secretobjs:
            ephemeral = minidom.parseString(i.XMLDesc(0)).\
                getElementsByTagName('secret')[0].\
                getAttribute('ephemeral')
            if ephemeral == 'no':
                return 1
        return 0

    elif flags == 'non-ephemeral':
        for i in secretobjs:
            ephemeral = minidom.parseString(i.XMLDesc(0)).\
                getElementsByTagName('secret')[0].\
                getAttribute('ephemeral')
            if ephemeral == 'yes':
                return 1
        return 0
    elif flags == 'private':
        for i in secretobjs:
            private = minidom.parseString(i.XMLDesc(0)).\
                getElementsByTagName('secret')[0].\
                getAttribute('private')
            if private == 'no':
                return 1
        return 0
    elif flags == 'non-private':
        for i in secretobjs:
            private = minidom.parseString(i.XMLDesc(0)).\
                getElementsByTagName('secret')[0].\
                getAttribute('private')
            if private == 'yes':
                return 1
        return 0
    return 1


def secretList(params):
    """list the existing secrets, can filtered the list result by flag:
       "ephemeral", "non-ephemeral", "private", "non-private"
    """
    global logger
    logger = params['logger']
    flags = params['flag']
    conn = sharedmod.libvirtobj['conn']

    try:
        logger.info("Total number of currently defined secrets: %d" %
                    conn.numOfSecrets())
        if conn.numOfSecrets() == 0:
            logger.info("There isn't any secret existing now.")
            return 0
        else:
            if flags == 'none':
                logger.info("list all secrets:")
                secretobjs = conn.listAllSecrets(0)
            else:
                logger.info("list %s secrets:" % flags)
                if flags == 'ephemeral':
                    secretobjs = conn.listAllSecrets(libvirt.
                                                     VIR_CONNECT_LIST_SECRETS_EPHEMERAL)
                elif flags == 'non-ephemeral':
                    secretobjs = conn.listAllSecrets(libvirt.
                                                     VIR_CONNECT_LIST_SECRETS_NO_EPHEMERAL)
                elif flags == 'private':
                    secretobjs = conn.listAllSecrets(libvirt.
                                                     VIR_CONNECT_LIST_SECRETS_PRIVATE)
                elif flags == 'non-private':
                    secretobjs = conn.listAllSecrets(libvirt.
                                                     VIR_CONNECT_LIST_SECRETS_NO_PRIVATE)
                else:
                    logger.error("the flags is wrong, must be one of 'none', \
                                 'ephemeral', 'no-ephemeral', 'private', \
                                 'no-private'")
                    return 1

            logger.info("UUID\t\t\t\tUsage")
            logger.info("----------------------------------------------------")
            for i in secretobjs:
                vol = minidom.parseString(i.XMLDesc(0)).\
                    getElementsByTagName('volume')[0].childNodes[0].data
                logger.info("%s %s %s" % (i.UUIDString(), i.usageType(), vol))
            ret = check_secretList(flags, secretobjs, conn)
            if ret:
                logger.info("list secrets failed.")
                return 1
            else:
                logger.info("list secrets successfully.")
                return 0

    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
