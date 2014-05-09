#!/usr/bin/evn python
# To test domain block device iotune

import time
import libxml2
import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ('guestname', 'bytes_sec', 'iops_sec')
optional_params = {}


def check_guest_status(domobj):
    """Check guest current status"""
    state = domobj.info()[0]
    if state == libvirt.VIR_DOMAIN_SHUTOFF or \
        state == libvirt.VIR_DOMAIN_SHUTDOWN:
        # add check function
        return False
    else:
        return True


def prepare_block_iotune(param, wbs, rbs, tbs, wis, ris, tis, logger):
    """prepare the block iotune parameter
    """
    logger.info("write_bytes_sec : %s" % wbs)
    param['write_bytes_sec'] = wbs
    logger.info("read_bytes_sec  : %s" % rbs)
    param['read_bytes_sec'] = rbs
    logger.info("total_bytes_sec : %s" % tbs)
    param['total_bytes_sec'] = tbs
    logger.info("write_iops_sec  : %s" % wis)
    param['write_iops_sec'] = wis
    logger.info("read_iops_sec   : %s" % ris)
    param['read_iops_sec'] = ris
    logger.info("total_iops_sec  : %s\n" % tis)
    param['total_iops_sec'] = tis
    return 0


def check_iotune(expected_param, result_param):
    """check block iotune configuration
    """
    for k in expected_param.keys():
        if expected_param[k] != result_param[k]:
            return 1
    return 0


def block_iotune(params):
    """Domain block device iotune"""
    logger = params['logger']
    guestname = params['guestname']
    bytes_sec = int(params['bytes_sec'])
    iops_sec = int(params['iops_sec'])
    flag = 0

    conn = sharedmod.libvirtobj['conn']

    domobj = conn.lookupByName(guestname)

    # Check domain block status
    if check_guest_status(domobj):
        pass
    else:
        domobj.create()
        time.sleep(90)

    try:
        xml = domobj.XMLDesc(0)
        doc = libxml2.parseDoc(xml)
        cont = doc.xpathNewContext()
        vdevs = cont.xpathEval("/domain/devices/disk/target/@dev")
        vdev = vdevs[0].content

        iotune_para = {'write_bytes_sec': 0L,
                       'total_iops_sec': 0L,
                       'read_iops_sec': 0L,
                       'read_bytes_sec': 0L,
                       'write_iops_sec': 0L,
                       'total_bytes_sec': 0L
                       }

        logger.info("prepare block iotune:")
        prepare_block_iotune(iotune_para, bytes_sec, bytes_sec, 0,
                             iops_sec, iops_sec, 0, logger)

        logger.info("start to set block iotune:")
        domobj.setBlockIoTune(vdev, iotune_para, flag)

        res = domobj.blockIoTune(vdev, flag)
        ret = check_iotune(iotune_para, res)
        if not ret:
            logger.info("set pass")
        else:
            logger.error("fails to set")
            return 1

        logger.info("prepare block iotune:")
        prepare_block_iotune(iotune_para, 0, 0, bytes_sec,
                             0, 0, iops_sec, logger)

        logger.info("start to set block iotune:")
        domobj.setBlockIoTune(vdev, iotune_para, flag)

        res = domobj.blockIoTune(vdev, flag)
        ret = check_iotune(iotune_para, res)
        if not ret:
            logger.info("set pass")
        else:
            logger.error("fails to set")
            return 1

    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
