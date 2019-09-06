#!/usr/bin/env python

import libvirt
import os

from libvirt import libvirtError
from utils import utils

required_params = {'guestname', 'checkpoint_name'}
optional_params = {'flags': None}


def check_dirty_bitmap(cp_name, logger):
    cmd = "virsh qemu-monitor-command test --pretty '{\"execute\": \"query-block\"}'"
    ret, out = utils.exec_cmd(cmd, shell=True)
    if ret:
        logger.error("exec cmd: %s failed." % cmd)
        return False
    logger.debug("out: %s" % out)
    if cp_name in ''.join(out):
        logger.info("%s in dirty bitmap." % cp_name)
        return True
    else:
        logger.info("%s not in dirty bitmap." % cp_name)
        return False


def checkpoint_delete(params):
    logger = params['logger']
    guestname = params['guestname']
    checkpoint_name = params['checkpoint_name']
    flag = utils.parse_flags(params)

    if not utils.version_compare('libvirt-python', 5, 6, 0, logger):
        logger.info("Current libvirt-python don't support checkpointCreateXML().")
        return 0

    logger.info("Checkpoint name: %s" % checkpoint_name)
    logger.info("flag: %s" % flag)
    try:
        conn = libvirt.open()
        dom = conn.lookupByName(guestname)
        cp = dom.checkpointLookupByName(checkpoint_name)
        cp_children_lists = []
        if (flag == libvirt.VIR_DOMAIN_CHECKPOINT_DELETE_CHILDREN or
                flag == libvirt.VIR_DOMAIN_CHECKPOINT_DELETE_CHILDREN_ONLY):
            cp_children = cp.listAllChildren()
            for children in cp_children:
                cp_children_lists.append(children.getName())
        cp.delete(flag)
    except libvirtError as err:
        logger.error("API error message: %s" % err.get_error_message())
        return 1

    if (flag == libvirt.VIR_DOMAIN_CHECKPOINT_DELETE_CHILDREN or
            flag == libvirt.VIR_DOMAIN_CHECKPOINT_DELETE_CHILDREN_ONLY):
        for cp_children in cp_children_lists:
            cp_xml_path = "/var/lib/libvirt/qemu/checkpoint/%s/%s.xml" % (guestname, cp_children)
            if os.path.exists(cp_xml_path):
                logger.error("FAIL: check checkpoint children %s failed." % cp_children)
                return 1
            else:
                logger.info("PASS: check checkpoint children %s successful." % cp_children)
            if check_dirty_bitmap(cp_children, logger):
                logger.error("FAIL: check %s dirty bitmap failed." % cp_children)
                return 1
            else:
                logger.info("PASS: check %s dirty bitmap successful." % cp_children)

    checkpoint_xml_path = "/var/lib/libvirt/qemu/checkpoint/%s/%s.xml" % (guestname, checkpoint_name)
    if flag == libvirt.VIR_DOMAIN_CHECKPOINT_DELETE_CHILDREN_ONLY:
        if not os.path.exists(checkpoint_xml_path):
            logger.error("FAIL: check %s xml path failed." % checkpoint_name)
            return 1
        else:
            logger.info("PASS: check %s xml path successful." % checkpoint_name)
    else:
        if os.path.exists(checkpoint_xml_path):
            logger.error("FAIL: check %s xml path failed." % checkpoint_name)
            return 1
        else:
            logger.info("PASS: check %s xml path successful." % checkpoint_name)

    if (flag == libvirt.VIR_DOMAIN_CHECKPOINT_DELETE_METADATA_ONLY or
            flag == libvirt.VIR_DOMAIN_CHECKPOINT_DELETE_CHILDREN_ONLY):
        if not check_dirty_bitmap(checkpoint_name, logger):
            logger.error("FAIL: check %s dirty bitmap failed." % checkpoint_name)
            return 1
        else:
            logger.info("PASS: check %s dirty bitmap successful." % checkpoint_name)
    else:
        if check_dirty_bitmap(checkpoint_name, logger):
            logger.error("FAIL: check %s dirty bitmap failed." % checkpoint_name)
            return 1
        else:
            logger.info("PASS: check %s dirty bitmap successful." % checkpoint_name)
    return 0


def checkpoint_delete_clean(params):
    logger = params['logger']
    checkpoint_name = params['checkpoint_name']
    guestname = params['guestname']
    flag = utils.parse_flags(params)

    conn = libvirt.open()
    dom_list = conn.listAllDomains()
    if len(dom_list) == 0:
        return 0
    if (flag == libvirt.VIR_DOMAIN_CHECKPOINT_DELETE_METADATA_ONLY and
            check_dirty_bitmap(checkpoint_name, logger)):
        cmd = ("virsh qemu-monitor-command test --pretty '"
               "{\"execute\" : \"block-dirty-bitmap-remove\", "
               "\"arguments\" : { \"node\" : \"drive-virtio-disk0\", "
               " \"name\" : \"%s\" }}'" % checkpoint_name)
        ret, out = utils.exec_cmd(cmd, shell=True)
        if ret:
            logger.error("exec cmd: %s failed." % cmd)

    dom = conn.lookupByName(guestname)
    cp_lists = dom.listAllCheckpoints()
    for cp in cp_lists:
        cp.delete()
