#!/usr/bin/env python
# volume wipe testing

import os
import string
import sys

from xml.dom import minidom
from libvirt import libvirtError
from src import sharedmod
from utils import utils

required_params = ('poolname', 'volname', 'volformat', 'capacity',)
optional_params = {'xml': 'xmls/dir_volume.xml',
                   }


def get_pool_path(poolobj):
    """ get pool xml description
    """
    poolxml = poolobj.XMLDesc(0)

    logger.debug("the xml description of pool is %s" % poolxml)

    doc = minidom.parseString(poolxml)
    path_element = doc.getElementsByTagName('path')[0]
    textnode = path_element.childNodes[0]
    path_value = textnode.data

    return path_value


def write_file(path, capacity):
    """write test data to file
    """
    logger.info("write %s data into file %s" % (capacity, path))
    out = utils.get_capacity_suffix_size(capacity)
    f = open(path, 'w')
    if sys.version_info[0] < 3:
        datastr = ''.join(string.lowercase + string.uppercase +
                          string.digits + '.' + '\n')
    else:
        datastr = ''.join(string.ascii_lowercase + string.ascii_uppercase +
                          string.digits + '.' + '\n')
    repeat = int(out['capacity_byte'] / 64)
    data = ''.join(repeat * datastr)
    f.write(data)
    f.close()


def dir_vol_wipe(params):
    """test volume download and check"""

    global logger
    logger = params['logger']
    poolname = params['poolname']
    volname = params['volname']
    volformat = params['volformat']
    capacity = params['capacity']
    xmlstr = params['xml']

    logger.info("the poolname is %s, volname is %s, volformat is %s" %
                (poolname, volname, volformat))

    conn = sharedmod.libvirtobj['conn']
    try:
        poolobj = conn.storagePoolLookupByName(poolname)
        path_value = get_pool_path(poolobj)
        volume_path = path_value + "/" + volname

        xmlstr = xmlstr.replace('VOLPATH', volume_path)
        xmlstr = xmlstr.replace('SUFFIX', capacity[-1])
        xmlstr = xmlstr.replace('CAP', capacity[:-1])
        logger.debug("volume xml:\n%s" % xmlstr)

        logger.info("create %s %s volume" % (volname, volformat))
        vol = poolobj.createXML(xmlstr, 0)

        write_file(volume_path, capacity)

        poolobj.refresh(0)

        origdigest = utils.digest(volume_path, 0, 0)
        logger.debug("the md5 hex digest of data read from %s is: %s" %
                     (volume_path, origdigest))

        test_path = path_value + "/" + "vol_test"
        out = utils.get_capacity_suffix_size(capacity)
        count = int(out['capacity_byte'] / 1024)
        logger.info("write %s zero to test volume %s" % (capacity, test_path))
        cmd = "dd if=/dev/zero of=%s bs=1024 count=%s" % (test_path, count)
        utils.exec_cmd(cmd, shell=True)
        cmpdigest = utils.digest(test_path, 0, 0)
        logger.debug("the compare volume digest is: %s" % cmpdigest)

        logger.info("wipe volume %s" % volume_path)
        vol.wipe(0)

        newdigest = utils.digest(volume_path, 0, 0)
        logger.debug("the volum digest of data read from %s after wipe is: %s"
                     % (volume_path, newdigest))

        logger.info("check the digest before and after wipe")
        if newdigest == origdigest:
            logger.error("wipe failed, digest did not change")
            return 1
        else:
            logger.info("digest is different before and after wipe")

        logger.info("compare the digest after wipe with digest of volume %s" %
                    test_path)
        if not newdigest == cmpdigest:
            logger.error("wipe failed, digest is different")
            return 1
        else:
            logger.info("digest is same with zero volume %s" % test_path)

        logger.info("wipe succeed")

    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    return 0


def dir_vol_wipe_clean(params):
    """clean testing environment"""
    poolname = params['poolname']
    volname = params['volname']

    conn = sharedmod.libvirtobj['conn']
    poolobj = conn.storagePoolLookupByName(poolname)
    path_value = get_pool_path(poolobj)
    test_path = path_value + "/" + "vol_test"

    vol = poolobj.storageVolLookupByName(volname)
    vol.delete(0)

    if os.path.exists(test_path):
        os.unlink(test_path)

    return 0
