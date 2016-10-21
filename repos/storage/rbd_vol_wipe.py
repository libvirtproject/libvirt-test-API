#!/usr/bin/env python
# volume wipe testing

import os
import commands
from src import sharedmod
from libvirt import libvirtError
from utils import utils

required_params = ('guestname', 'cephserver', 'cephserverpool', 'poolname', 'volname', 'alg',)
optional_params = {'xml': 'xmls/rbd_disk.xml',}


def write_img(ip, logger):
    cmd = "mkfs.ext4 /dev/vdb"
    logger.debug("write_img: cmd: %s" % cmd)
    ret, out = utils.remote_exec_pexpect(ip, "root", "redhat", cmd)
    if ret:
        logger.error("write img failed: %s" % out)
        return 1

    cmd = "mount /dev/vdb /mnt"
    logger.debug("write_img: cmd: %s" % cmd)
    ret, out = utils.remote_exec_pexpect(ip, "root", "redhat", cmd)
    if ret:
        logger.error("write img failed: %s" % out)
        return 1

    cmd = "touch /mnt/test-api-file"
    logger.debug("write_img: cmd: %s" % cmd)
    ret, out = utils.remote_exec_pexpect(ip, "root", "redhat", cmd)
    if ret:
        logger.error("write img failed: %s" % out)
        return 1

    cmd = "for i in {1..500}; do echo \"for test\" >> /mnt/test-api-file; done"
    logger.debug("write_img: cmd: %s" % cmd)
    ret, out = utils.remote_exec_pexpect(ip, "root", "redhat", cmd, 360)
    if ret:
        logger.error("write img failed: %s" % out)
        return 1

    cmd = "umount /mnt"
    logger.debug("write_img: cmd: %s" % cmd)
    ret, out = utils.remote_exec_pexpect(ip, "root", "redhat", cmd)
    if ret:
        logger.error("write img failed: %s" % out)
        return 1


def get_size(cephserver, cephserverpool, poolname, volname, logger):
    cmd = ("rbd -m %s -p %s du %s | grep %s" %
           (cephserver, cephserverpool, volname, volname))
    logger.debug("get_size: cmd: %s" % cmd)
    ret, out = commands.getstatusoutput(cmd)
    if ret:
        logger.error("get_size: failed.")
        logger.error("out: %s" % out)
        return

    warn_str = ("warning: fast-diff map is not enabled for %s. operation "
                "may be slow.\n" % volname)
    image_size = ''
    if warn_str in out:
        image_size = filter(None, out.strip(warn_str).split(' '))[1]
    else:
        image_size = filter(None, out.split(' '))[2]
    return image_size


def rbd_vol_wipe(params):
    """test rbd volume wipe"""

    global logger
    logger = params['logger']
    cephserver = params['cephserver']
    cephserverpool = params['cephserverpool']
    poolname = params['poolname']
    volname = params['volname']
    alg = params['alg']
    xmlstr = params['xml']
    guestname = params['guestname']

    logger.info("ceph server: %s, ceph server pool: %s" % (cephserver, cephserverpool))
    logger.info("the poolname is %s, volname is %s, alg is %s" %
                (poolname, volname, alg))

    sourcename = "%s/%s" % (cephserverpool, volname)
    xmlstr = xmlstr.replace('SOURCENAME', sourcename)
    xmlstr = xmlstr.replace('CEPHSERVER', cephserver)

    try:
        conn = sharedmod.libvirtobj['conn']
        domobj = conn.lookupByName(guestname)
        domobj.attachDevice(xmlstr)

        mac = utils.get_dom_mac_addr(guestname)
        ip = utils.mac_to_ip(mac, 120)
        logger.info("guest ip is %s" % ip)
        write_img(ip, logger)

        before_size = get_size(cephserver, cephserverpool, poolname, volname, logger)
        logger.info("before wipe, img used is %s" % before_size)

        poolobj = conn.storagePoolLookupByName(poolname)
        vol = poolobj.storageVolLookupByName(volname)
        vol.wipePattern(int(alg), 0)

        after_size = get_size(cephserver, cephserverpool, poolname, volname, logger)
        logger.info("after wipe, img used is %s" % after_size)
        if after_size != "0" or before_size == "0":
            logger.error("rbd vol wipe failed.")
            return 1

        logger.info("rbd vol wipe succeed")

    except libvirtError, e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    return 0


def rbd_vol_wipe_clean(params):
    """clean testing environment"""
    cephserver = params['cephserver']
    cephserverpool = params['cephserverpool']
    poolname = params['poolname']
    volname = params['volname']

    # rbd -m 10.73.75.52 -p libvirt-pool rm rbd_vol.img
    cmd = "rbd -m %s -p %s rm %s" % (cephserver, cephserverpool, volname)
    logger.debug("rbd_vol_wipe_clean: cmd: %s" % cmd)
    stat, ret = commands.getstatusoutput(cmd)
    if stat:
        logger.error("rbd_vol_wipe_clean: rm volume failed.")
        logger.error("ret: %s" % ret)
