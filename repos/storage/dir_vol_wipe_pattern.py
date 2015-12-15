#!/usr/bin/env python
# volume wipe with pattern testing, the supported algorithm are
# zero and algorithm patterns supported by 'scrub' command which
# are nnsa|dod|bsi|gutmann|schneier|pfitzner7|pfitzner33|random

import os
import string
from xml.dom import minidom

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('poolname', 'volname', 'volformat', 'capacity', 'algorithm',)
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
    datastr = ''.join(string.lowercase + string.uppercase +
                      string.digits + '.' + '\n')
    repeat = out['capacity_byte'] / 64
    data = ''.join(repeat * datastr)
    f.write(data)
    f.close()


def dir_vol_wipe_pattern(params):
    """test volume download and check"""

    global logger
    logger = params['logger']
    poolname = params['poolname']
    volname = params['volname']
    volformat = params['volformat']
    capacity = params['capacity']
    algorithm = params['algorithm']
    xmlstr = params['xml']

    logger.info("the poolname is %s, volname is %s, volformat is %s" %
                (poolname, volname, volformat))

    logger.info("the wipe algorithm given is %s" % algorithm)
    alg_str = 'libvirt.VIR_STORAGE_VOL_WIPE_ALG_%s' % algorithm.upper()
    alg_val = eval(alg_str)
    logger.info("the correspond algorithm value is %s" % alg_val)

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

        logger.info("wipe volume %s with algorithm value %s" %
                    (volume_path, alg_val))
        vol.wipePattern(alg_val, 0)

        newdigest = utils.digest(volume_path, 0, 0)
        logger.debug("the volum digest of data read from %s after wipe is: %s"
                     % (volume_path, newdigest))

        logger.info("check the digest before and after wipe")
        if newdigest == origdigest:
            logger.error("wipe with algorithm %s failed, digest is the same"
                         % algorithm)
            return 1
        else:
            logger.info("digest is different before and after wipe")

        logger.info("wipe with algorithm %s succeed" % algorithm)

    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    return 0


def dir_vol_wipe_pattern_clean(params):
    """clean testing environment"""
    poolname = params['poolname']
    volname = params['volname']

    conn = sharedmod.libvirtobj['conn']
    poolobj = conn.storagePoolLookupByName(poolname)
    vol = poolobj.storageVolLookupByName(volname)
    vol.delete(0)

    return 0
