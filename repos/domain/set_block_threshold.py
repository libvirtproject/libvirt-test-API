#!/usr/bin/env python
# To test setBlockThreshold() API

from libvirt import libvirtError
from src import sharedmod
from utils import utils
from utils.utils import parse_flags, del_file

required_params = ('guestname', 'threshold')
optional_params = {'flags': None, }

TEST_IMG = "/var/lib/libvirt/images/test-api-block.img"


def set_block_threshold(params):
    """ Test setBlockThreshold()
    """
    logger = params['logger']
    guestname = params['guestname']
    threshold = params['threshold']
    flags = parse_flags(params, param_name='flags')

    logger.info("threshold: %s, flags: %s" % (threshold, flags))

    if not utils.version_compare("libvirt-python", 3, 2, 0, logger):
        logger.info("Current libvirt-python don't support this API.")
        return 0
    if utils.check_qemu_package("qemu-kvm"):
        logger.info("Current qemu-kvm don't support this API.")
        return 0

    if not del_file(TEST_IMG, logger):
        return 1

    disk_xml = ('<disk device="disk" type="file"><driver name="qemu" type="raw"/>'
                '<source file="%s"/>'
                '<target bus="virtio" dev="vdb"/></disk>' % TEST_IMG)

    cmd = "qemu-img create -f raw %s 2G" % TEST_IMG
    ret, out = utils.exec_cmd(cmd, shell=True)
    if ret:
        logger.error("create img failed. cmd: %s, out: %s" % (cmd, out))
        return 1

    try:
        conn = sharedmod.libvirtobj['conn']
        dom = conn.lookupByName(guestname)
        dom.attachDevice(disk_xml)
        dom.setBlockThreshold('vdb', int(threshold), flags)
    except libvirtError as e:
        logger.error("API error message: %s, error code: %s" %
                     (e.get_error_message(), e.get_error_code()))
        return 1

    cmd = "virsh domstats %s --block | grep 'threshold'" % guestname
    ret, out = utils.exec_cmd(cmd, shell=True)
    logger.debug("out: %s" % out)
    if ret:
        logger.error("get threshold failed. cmd: %s, out: %s" % (cmd, out))
        return 1

    if out[0].split('=')[1] != threshold:
        logger.error("FAIL: check threshold failed. threshold: %s" % out)
        return 1
    else:
        logger.info("PASS: check threshold successful.")

    mac = utils.get_dom_mac_addr(guestname)
    ip = utils.mac_to_ip(mac, 120)
    logger.info("guest ip is %s" % ip)

    cmd = "mkfs.ext4 /dev/vdb"
    ret, out = utils.remote_exec_pexpect(ip, "root", "redhat", cmd)
    if ret:
        logger.error("write img failed: %s" % out)
        return 1

    del_file(TEST_IMG, logger)

    return 0
