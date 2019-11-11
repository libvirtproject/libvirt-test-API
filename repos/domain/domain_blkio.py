#!/usr/bin/evn python
# To test domain blkio parameters

import os
import re
import time
import libvirt

from libvirt import libvirtError
from utils import process
from utils.utils import get_xml_value
from utils import utils

BLKIO_PATH1 = "/cgroup/blkio/libvirt/qemu/%s"
BLKIO_PATH2 = "/sys/fs/cgroup/blkio/machine.slice/machine-qemu\\x2d%s.scope"
BLKIO_PATH_BASE = "/sys/fs/cgroup/blkio/machine.slice"
BLKIO_PATH_RE = "machine-qemu.*?%s.scope"
GET_PARTITION = "df -P %s | tail -1 | awk {'print $1'}"

required_params = ('guestname', 'weight',)
optional_params = {}


def get_blkio_path(guestname, logger):
    logger.info("Check " + BLKIO_PATH1 % guestname)
    if os.path.exists(BLKIO_PATH1 % guestname):
        return BLKIO_PATH1 % guestname
    elif os.path.exists(BLKIO_PATH2 % guestname):
        return BLKIO_PATH2 % guestname
    else:
        logger.warn("CGroup path is not in expected format")
        for path in os.listdir(BLKIO_PATH_BASE):
            logger.info("Check " + path)
            if re.match(BLKIO_PATH_RE % guestname, path):
                return BLKIO_PATH_BASE + "/" + path
            if re.match(BLKIO_PATH_RE % guestname.replace('_', ''), path):
                return BLKIO_PATH_BASE + "/" + path


def get_output(command, logger):
    """execute shell command
    """
    ret = process.run(command, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("executing " + "\"" + command + "\"" + " failed")
        logger.error(ret.stdout)
    return ret.exit_status, ret.stdout


def get_device(domobj, logger):
    """get the disk device which domain image stored in
    """
    xml_path = "/domain/devices/disk/source/@file"
    image_file = get_xml_value(domobj, xml_path)
    status, output = get_output(GET_PARTITION % image_file[0], logger)

    if output.startswith('/dev/mapper'):
        # BUG: Call 'lvs' in python will cause unexpected file descriptor leak
        # so we have to ignore stderr.
        cmd = 'lvs "%s" -o devices 2>/dev/null | tail -1 | cut -d "(" -f 1' % output
        ret = process.run(cmd, shell=True, ignore_status=True)
        output = ret.stdout.strip()

    if not status:
        return output[:-1]
    else:
        logger.error("get device error: ")
        logger.error(GET_PARTITION % image_file)
        return ""


def set_device_scheduler(dev, logger):
    if not dev.startswith('/dev'):
        logger.error('Invalid device path: ' + str(dev))
    dev = dev[5:]
    scheduler = "/sys/block/%s/queue/scheduler" % dev
    cmd = "cat %s" % scheduler
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("check scheduler file failed: %s" % ret.stdout)
        return 1
    if "cfq" in ret.stdout:
        logger.info("set scheduler to cfq.")
        with open(scheduler, 'w') as scheduler_file:
            scheduler_file.write("cfq")
    elif "bfq" in ret.stdout:
        logger.info("set scheduler to bfq.")
        with open(scheduler, 'w') as scheduler_file:
            scheduler_file.write("bfq")
    else:
        logger.info("Don't support to set scheduler in this kernel version.")


def check_blkio_paras(blkio_path, blkio_paras, logger):
    """check blkio parameters according to cgroup filesystem
    """
    blkio_path = blkio_path.replace('\\', '\\\\')
    logger.info("checking blkio parameters from cgroup")
    if 'weight' in blkio_paras:
        expected_weight = blkio_paras['weight']
        if utils.isRelease(8, logger):
            status, output = get_output("cat %s/blkio.bfq.weight" % blkio_path, logger)
        else:
            status, output = get_output("cat %s/blkio.weight" % blkio_path, logger)
        if not status:
            logger.info("blkio weight: %s" % output)
        else:
            return 1

        if int(output) == expected_weight:
            logger.info("the weight matches")
            return 0
        else:
            logger.error("the weight mismatches")
            return 1

    if 'device_weight' in blkio_paras:
        expected_device_weight = blkio_paras['device_weight']
        status, output = get_output("cat %s/blkio.weight_device"
                                    % blkio_path, logger)
        if not status:
            logger.info("%s/blkio.weight_device is \"%s\""
                        % (blkio_path, output))
        else:
            return 1

        if len(output) != 0 and output.split()[1] == expected_device_weight.split(',')[1]:
            logger.info("the device_weight matches with cgroup "
                        "blkio.weight_device")
            return 0
        else:
            logger.error("the device_weight mismatches with cgroup "
                         "blkio.weight_device")
            return 1

    return 0


def check_guest_status(domobj):
    """Check guest current status"""
    state = domobj.info()[0]
    if state == libvirt.VIR_DOMAIN_SHUTOFF or \
            state == libvirt.VIR_DOMAIN_SHUTDOWN:
        # add check function
        return False
    else:
        return True


def domain_blkio(params):
    """domain blkio parameters test function"""
    logger = params['logger']
    guestname = params['guestname']
    expected_weight = params['weight']
    flag = 0

    try:
        conn = libvirt.open()
        domobj = conn.lookupByName(guestname)

        # Check domain block status
        if check_guest_status(domobj):
            pass
        else:
            domobj.create()
            time.sleep(90)

        device = get_device(domobj, logger)
        set_device_scheduler(device, logger)
        logger.info("get weight from blkioParameters().")
        blkio_paras = domobj.blkioParameters(flag)
        logger.info("blkio weight: %d" % blkio_paras['weight'])
        blkio_path = get_blkio_path(guestname, logger)
        status = check_blkio_paras(blkio_path, blkio_paras, logger)
        if status != 0:
            return 1

        logger.info("set weight to %s" % expected_weight)
        blkio_paras = {'weight': int(expected_weight)}
        status = domobj.setBlkioParameters(blkio_paras, flag)
        if status != 0:
            return 1
        status = check_blkio_paras(blkio_path, blkio_paras, logger)
        if status != 0:
            return 1

        # Don't support blkio device weight on RHEL 8
        if not utils.isRelease('8', logger):
            device_weight = "%s,%s" % (device, expected_weight)
            logger.info("set device_weight to %s" % device_weight)
            blkio_paras = {'device_weight': device_weight}
            status = domobj.setBlkioParameters(blkio_paras, flag)
            if status != 0:
                return 1
            status = check_blkio_paras(blkio_path, blkio_paras, logger)
            if status != 0:
                return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    return 0
