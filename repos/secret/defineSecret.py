#!/usr/bin/evn python

import os
import libvirt

from libvirt import libvirtError
from src import sharedmod
from xml.dom import minidom
from utils import utils

required_params = ('ephemeral', 'private', 'secretUUID', 'usagetype',)
optional_params = {'xml': 'xmls/secret.xml',
                   'diskpath': '',
                   'tlsname': '',
                   'vtpmname': ''
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
        return 1

    secret_xml['ephemeral'] = (XMLFile.getElementsByTagName('secret')[0]).\
        getAttribute('ephemeral')
    secret_xml['private'] = (XMLFile.getElementsByTagName('secret')[0]).\
        getAttribute('private')
    secret_xml['secretUUID'] = (XMLFile.getElementsByTagName('uuid')[0]).\
        childNodes[0].data

    if secret_params['usage_type'] == 'volume':
        secret_xml['diskpath'] = (XMLFile.getElementsByTagName('volume')[0]).\
            childNodes[0].data
    elif secret_params['usage_type'] == 'tls':
        if utils.version_compare("libvirt-python", 2, 5, 0, logger):
            secret_xml['tlsname'] = (XMLFile.getElementsByTagName('name')[0]).\
                childNodes[0].data
    elif secret_params['usage_type'] == 'vtpm':
        if utils.version_compare("libvirt-python", 5, 6, 0, logger):
            secret_xml['vtpmname'] = (XMLFile.getElementsByTagName('name')[0]).\
                childNodes[0].data
    else:
        logger.error("unexpected secret usage type: %s" % secret_params['usage_type'])
        return 1

    for i in list(secret_xml.keys()):
        if secret_xml[i] != secret_params[i]:
            return 1

    return 0


def defineSecret(params):
    """Define a secret from xml"""
    global logger

    logger = params['logger']
    xmlstr = params['xml']
    secret_params = {}
    secret_params['ephemeral'] = params['ephemeral']
    secret_params['private'] = params['private']
    secret_params['secretUUID'] = params['secretUUID']
    secret_params['usage_type'] = params['usagetype']

    if secret_params['usage_type'] == 'volume':
        secret_params['diskpath'] = params['diskpath']
        disk_create = "qemu-img create %s 10M" % secret_params['diskpath']
        logger.info("create disk: %s" % secret_params['diskpath'])
        (status, message) = utils.exec_cmd(disk_create, shell=True)
        if status != 0:
            logger.debug(message)
            return 1
        xmlstr = xmlstr.replace('DISKPATH', secret_params['diskpath'])
    elif secret_params['usage_type'] == 'tls':
        if utils.version_compare("libvirt-python", 2, 5, 0, logger):
            secret_params['tlsname'] = params['tlsname']
        else:
            logger.info("Current libvirt-python don't support 'tls'.")
            return 0
    elif secret_params['usage_type'] == 'vtpm':
        if utils.version_compare("libvirt-python", 5, 6, 0, logger):
            secret_params['vtpmname'] = params['vtpmname']
        else:
            logger.info("Current libvirt-python don't support 'vtpm'.")
            return 0
    else:
        logger.error("unexpected secret usage type: %s" % secret_params['usage_type'])
        return 1

    xmlstr = xmlstr.replace('EPHEMERAL', secret_params['ephemeral'])
    xmlstr = xmlstr.replace('PRIVATE', secret_params['private'])
    xmlstr = xmlstr.replace('SECRETUUID', secret_params['secretUUID'])
    logger.debug("secret xml:\n%s" % xmlstr)
    conn = sharedmod.libvirtobj['conn']

    try:
        secretobj = conn.secretDefineXML(xmlstr, 0)

        if not check_defineSecret(secret_params, secretobj):
            logger.info("define secret %s is successful:\n %s" %
                        (secret_params['secretUUID'], secretobj.XMLDesc(0)))
        else:
            logger.error("fail to check define secret")
            return 1

    except libvirtError as err:
        logger.error("API error message: %s, error code is %s"
                     % (err.get_error_message(), err.get_error_code()))
        return 1

    return 0


def defineSecret_clean(params):
    """clean env"""
    secretUUID = params['secretUUID']
    usage_type = params['usagetype']

    if usage_type == 'volume':
        diskpath = params['diskpath']
        os.remove(diskpath)
    elif usage_type == 'tls':
        if utils.version_compare("libvirt-python", 2, 5, 0, logger):
            conn = libvirt.open(None)
            secretobj = conn.secretLookupByUUIDString(secretUUID)
            secretobj.undefine()
    elif usage_type == 'vtpm':
        if utils.version_compare("libvirt-python", 5, 6, 0, logger):
            conn = libvirt.open(None)
            secretobj = conn.secretLookupByUUIDString(secretUUID)
            secretobj.undefine()
