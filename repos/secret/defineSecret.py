#!/usr/bin/evn python

from libvirt import libvirtError
from src import sharedmod
from xml.dom import minidom
from utils import utils

required_params = ('ephemeral', 'private', 'secretUUID', 'diskpath',)
optional_params = {'xml': 'xmls/secret.xml',
                   }


def check_defineSecret(secret_params, secretobj):
    """Check define secret result, while the value of ephemeral is no, the
       generated xml will exist under /etc/libvirt/secrets/; while the value of
       ephemeral is yes, it means the secret file is temporary, so check via
       the dumpxml of the secret.
    """
    secret_xml = {}
    if secret_params['ephemeral'] == 'no':
        XMLFile = minidom.parse("/etc/libvirt/secrets/%s.xml" %
                                secretobj.UUIDString())
    elif secret_params['ephemeral'] == 'yes':
        XMLFile = minidom.parseString(secretobj.XMLDesc(0))
    else:
        logger.error("The value of ephemeral is wrong, please input \"yes\" "
                     "or \"no\" for this value")
        return 0

    secret_xml['ephemeral'] = (XMLFile.getElementsByTagName('secret')[0]).\
        getAttribute('ephemeral')
    secret_xml['private'] = (XMLFile.getElementsByTagName('secret')[0]).\
        getAttribute('private')
    secret_xml['secretUUID'] = (XMLFile.getElementsByTagName('uuid')[0]).\
        childNodes[0].data
    secret_xml['diskpath'] = (XMLFile.getElementsByTagName('volume')[0]).\
        childNodes[0].data

    for i in secret_xml.keys():
        if secret_xml[i] != secret_params[i]:
            return 0

    return 1


def defineSecret(params):
    """Define a secret from xml"""
    global logger

    logger = params['logger']
    secret_params = {}
    secret_params['ephemeral'] = params['ephemeral']
    secret_params['private'] = params['private']
    secret_params['secretUUID'] = params['secretUUID']
    secret_params['diskpath'] = params['diskpath']
    xmlstr = params['xml']
    logger.debug("secret xml:\n%s" % xmlstr)

    """Create the volume
    """
    disk_create = "qemu-img create %s 10M" % secret_params['diskpath']
    print disk_create
    logger.debug("the command line of creating disk images is '%s'" %
                 disk_create)
    (status, message) = utils.exec_cmd(disk_create, shell=True)
    if status != 0:
        logger.debug(message)
        return 1

    conn = sharedmod.libvirtobj['conn']

    try:
        secretobj = conn.secretDefineXML(xmlstr, 0)

        if check_defineSecret(secret_params, secretobj):
            logger.info("define secret %s is successful:\n %s" %
                        (secret_params['secretUUID'], secretobj.XMLDesc(0)))
        else:
            logger.error("fail to check define secret")
            return 1

    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
