#!/usr/bin/env python

import commands
import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('poolname',
                   'volname',
                   'cephserver',
                   'cephserverpool',
                   'flags',)
optional_params = {'snapshotname': ''}


def prepare_snapshot(cephserver, cephserverpool, volname, sn, logger):
    cmd = "rbd -m %s snap create %s/%s@%s" % (cephserver, cephserverpool, volname, sn)
    logger.debug("prepare_snapshot: cmd: %s" % cmd)
    stat, ret = commands.getstatusoutput(cmd)
    if stat == 1:
        logger.error("prepare_snapshot: create snapshot failed")
        logger.error("ret: %s" % ret)
        return 1

    return 0


def check_volume(cephserver, cephserverpool, volname, logger):
    cmd = "rbd -m %s -p %s ls | grep %s" % (cephserver, cephserverpool, volname)
    logger.debug("check_volume: cmd: %s" % cmd)
    stat, ret = commands.getstatusoutput(cmd)
    if stat == 0:
        logger.error("check_volume: delete failed, volume still exists.")
        logger.error("ret: %s" % ret)
        return 1

    return 0


def delete_rbd_volume(params):
    """test volume delete with flags"""

    global logger
    logger = params['logger']
    poolname = params['poolname']
    volname = params['volname']
    sn = params.get('snapshotname', '')
    cephserver = params['cephserver']
    cephserverpool = params['cephserverpool']
    flags = params['flags']

    logger.info("the poolname is %s, volname is %s, snapshot name is %s" %
                (poolname, volname, sn))
    logger.info("ceph server is %s, ceph server pool is %s" %
                (cephserver, cephserverpool))
    logger.info("the flags given is %s" % flags)

    if sn:
        ret = prepare_snapshot(cephserver, cephserverpool, volname, sn, logger)
        if ret == 1:
            return 1

    try:
        conn = sharedmod.libvirtobj['conn']
        poolobj = conn.storagePoolLookupByName(poolname)
        vol = poolobj.storageVolLookupByName(volname)
        vol.delete(int(flags))

        if check_volume(cephserver, cephserverpool, volname, logger):
            return 1

    except libvirtError, e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    return 0
