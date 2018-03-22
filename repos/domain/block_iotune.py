#!/usr/bin/evn python
# To test domain block device iotune

import time
import libxml2
import libvirt
from libvirt import libvirtError
from utils import utils
from src import sharedmod

required_params = ('guestname',)
optional_params = {'total_bytes_sec': '',
                   'read_bytes_sec': '',
                   'write_bytes_sec': '',
                   'total_iops_sec': '',
                   'read_iops_sec': '',
                   'write_iops_sec': '',
                   'total_bytes_sec_max': '',
                   'read_bytes_sec_max': '',
                   'write_bytes_sec_max': '',
                   'total_iops_sec_max': '',
                   'read_iops_sec_max': '',
                   'write_iops_sec_max': '',
                   'size_iops_sec': '',
                   'total_bytes_sec_max_length': '',
                   'read_bytes_sec_max_length': '',
                   'write_bytes_sec_max_length': '',
                   'total_iops_sec_max_length': '',
                   'read_iops_sec_max_length': '',
                   'write_iops_sec_max_length': '',
                   'group_name': ''
                   }


def check_guest_status(domobj):
    """Check guest current status"""
    state = domobj.info()[0]
    if state == libvirt.VIR_DOMAIN_SHUTOFF or \
            state == libvirt.VIR_DOMAIN_SHUTDOWN:
        # add check function
        return False
    else:
        return True


def prepare_block_iotune(params, logger):
    """prepare the block iotune parameter
    """
    params_list = {}
    # libvirt-python version >= 3.0.0
    if utils.version_compare("libvirt-python", 3, 0, 0, logger):
        name_list = ('total_bytes_sec', 'read_bytes_sec', 'write_bytes_sec',
                     'total_iops_sec', 'read_iops_sec', 'write_iops_sec',
                     'total_bytes_sec_max', 'read_bytes_sec_max',
                     'write_bytes_sec_max', 'total_iops_sec_max',
                     'read_iops_sec_max', 'write_iops_sec_max',
                     'size_iops_sec', 'total_bytes_sec_max_length',
                     'read_bytes_sec_max_length', 'write_bytes_sec_max_length',
                     'total_iops_sec_max_length', 'read_iops_sec_max_length',
                     'write_iops_sec_max_length', 'group_name')
    else:
        name_list = ('total_bytes_sec', 'read_bytes_sec', 'write_bytes_sec',
                     'total_iops_sec', 'read_iops_sec', 'write_iops_sec')
    for i in name_list:
        if params.get(i) is not None:
            if i == "group_name":
                params_list[i] = params.get(i)
            else:
                params_list[i] = int(params.get(i))

    logger.info("Params list: %s" % params_list)
    return params_list


def check_iotune(expected_param, result_param):
    """check block iotune configuration
    """
    for k in list(expected_param.keys()):
        if expected_param[k] != result_param[k]:
            return 1
    return 0


def block_iotune(params):
    """Domain block device iotune"""
    logger = params['logger']
    guestname = params['guestname']
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

        logger.info("prepare block iotune:")
        iotune_param = prepare_block_iotune(params, logger)

        if len(iotune_param) == 0:
            logger.info("block iotune: parameter is empty.")
            return 0

        logger.info("start to set block iotune:")
        domobj.setBlockIoTune(vdev, iotune_param, flag)

        res = domobj.blockIoTune(vdev, flag)
        logger.info("Set block iotune: %s" % res)
        ret = check_iotune(iotune_param, res)
        if not ret:
            logger.info("set pass")
        else:
            logger.error("fails to set")
            return 1

    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    return 0
