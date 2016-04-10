#!/usr/bin/env python
# dir storage volume download testing

import os
import string
from xml.dom import minidom
from libvirt import libvirtError
from src import sharedmod
from utils import utils

required_params = ('poolname', 'volname', 'volformat', 'capacity', 'offset',
                   'length',)
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


def handler(stream, data, file_):
    return file_.write(data)


def dir_vol_download(params):
    """test volume download and check"""

    global logger
    logger = params['logger']
    poolname = params['poolname']
    volname = params['volname']
    volformat = params['volformat']
    offset = int(params['offset'])
    length = int(params['length'])
    capacity = params['capacity']
    xmlstr = params['xml']

    logger.info("the poolname is %s, volname is %s, volformat is %s" %
                (poolname, volname, volformat))
    logger.info("download offset is: %s" % offset)
    logger.info("the data length to download is: %s" % length)

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
        origdigest = utils.digest(volume_path, offset, length)
        logger.debug("the md5 hex digest of data read from %s is: %s" %
                     (volume_path, origdigest))

        st = conn.newStream(0)

        test_path = path_value + "/" + "vol_test"

        f = open(test_path, 'w')
        logger.info("start download")
        vol.download(st, offset, length, 0)
        logger.info("downloaded all data")
        st.recvAll(handler, f)
        logger.info("finished stream")
        st.finish()
        f.close()

        newdigest = utils.digest(test_path, 0, 0)
        logger.debug("the md5 hex digest of data read from %s is: %s" %
                     (test_path, newdigest))

        if origdigest == newdigest:
            logger.info("file digests match, download succeed")
        else:
            logger.error("file digests not match, download failed")
            return 1

    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    return 0


def dir_vol_download_clean(params):
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
