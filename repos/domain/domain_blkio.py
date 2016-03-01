#!/usr/bin/evn python
# To test domain blkio parameters

import os
import time
import libxml2
import libvirt
import commands
from libvirt import libvirtError

from src import sharedmod

CGROUP_PATH = "/cgroup"
BLKIO_PATH1 = "%s/blkio/libvirt/qemu/%s"
BLKIO_PATH2 = "/sys/fs%s/blkio/machine.slice/machine-qemu\\\\x2d%s.scope"
GET_PARTITION = "df -P %s | tail -1 | awk {'print $1'}"

required_params = ('guestname', 'weight',)
optional_params = {}


def get_output(command, logger):
    """execute shell command
    """
    status, ret = commands.getstatusoutput(command)
    if status:
        logger.error("executing " + "\"" + command + "\"" + " failed")
        logger.error(ret)
    return status, ret


def get_device(domobj, logger):
    """get the disk device which domain image stored in
    """
    xml = domobj.XMLDesc(0)
    doc = libxml2.parseDoc(xml)
    cont = doc.xpathNewContext()
    devs = cont.xpathEval("/domain/devices/disk/source/@file")
    image_file = devs[0].content

    status, output = get_output(GET_PARTITION % image_file, logger)

    if output.startswith('/dev/mapper'):
        # BUG: Call 'lvs' in python will cause unexpected file descriptor leak
        # so we have to ignore stderr.
        output = commands.getoutput('lvs "%s" -o devices 2>/dev/null | tail -1 | cut -d "(" -f 1'
                                    % output).strip()

    if not status:
        return output[:-1]
    else:
        logger.error("get device error: ")
        logger.error(GET_PARTITION % image_file)
        return ""


def check_blkio_paras(domain_blkio_path, domainname, blkio_paras, logger):
    """check blkio parameters according to cgroup filesystem
    """
    logger.info("checking blkio parameters from cgroup")
    if 'weight' in blkio_paras:
        expected_weight = blkio_paras['weight']
        status, output = get_output("cat %s/blkio.weight"
                                    % domain_blkio_path, logger)
        if not status:
            logger.info("%s/blkio.weight is \"%s\""
                        % (domain_blkio_path, output))
        else:
            return 1

        if int(output) == expected_weight:
            logger.info("the weight matches with cgroup blkio.weight")
            return 0
        else:
            logger.error("the weight mismatches with cgroup blkio.weight")
            return 1

    if 'device_weight' in blkio_paras:
        expected_device_weight = blkio_paras['device_weight']
        status, output = get_output("cat %s/blkio.weight_device"
                                    % domain_blkio_path, logger)
        if not status:
            logger.info("%s/blkio.weight_device is \"%s\""
                        % (domain_blkio_path, output))
        else:
            return 1

        if output.split()[1] == expected_device_weight.split(',')[1]:
            logger.info("the device_weight matches with cgroup \
                        blkio.weight_device")
            return 0
        else:
            logger.error("the device_weight mismatches with cgroup \
                        blkio.weight_device")
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

    conn = sharedmod.libvirtobj['conn']

    domobj = conn.lookupByName(guestname)

    # Check domain block status
    if check_guest_status(domobj):
        pass
    else:
        domobj.create()
        time.sleep(90)

    if os.path.exists(CGROUP_PATH):
        blkio_path = BLKIO_PATH1 % (CGROUP_PATH, guestname)
    else:
        blkio_path = BLKIO_PATH2 % (CGROUP_PATH, guestname)

    try:
        blkio_paras = domobj.blkioParameters(flag)

        logger.info("the blkio weight of %s is: %d"
                    % (guestname, blkio_paras['weight']))

        status = check_blkio_paras(blkio_path, guestname, blkio_paras,
                                   logger)
        if status != 0:
            return 1

        logger.info("start to set param weight to %s" % expected_weight)
        blkio_paras = {'weight': int(expected_weight)}
        status = domobj.setBlkioParameters(blkio_paras, flag)
        if status != 0:
            return 1

        status = check_blkio_paras(blkio_path, guestname, blkio_paras,
                                   logger)
        if status != 0:
            return 1

        device = get_device(domobj, logger)
        device_weight = "%s,%s" % (device, expected_weight)
        logger.info("start to set param device_weight to %s"
                    % device_weight)
        blkio_paras = {'device_weight': device_weight}
        status = domobj.setBlkioParameters(blkio_paras, flag)
        if status != 0:
            return 1

        status = check_blkio_paras(blkio_path, guestname, blkio_paras,
                                   logger)
        if status != 0:
            return 1

    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0
