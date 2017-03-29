#!/usr/bin/evn python
# To test blockpull()

import lxml
import lxml.etree
import os
import time

import libvirt
from libvirt import libvirtError

from utils import utils
from utils.utils import parse_flags, get_rand_str

required_params = ('guestname', 'bandwidth', 'flags',)
optional_params = {}


def get_path(dom):
    dom_xml = dom.XMLDesc(0)
    tree = lxml.etree.fromstring(dom_xml)
    return tree.xpath("/domain/devices/disk/target/@dev")


def del_img(img):
    if os.path.exists(img):
        cmd = 'rm -f %s' % (img)
        ret, out = utils.exec_cmd(cmd, shell=True)
        if ret:
            logger.error("delete img failed. cmd: %s, out: %s" % (cmd, out))
            return False

    return True


def block_pull(params):
    """domain blockPull test function
    """
    logger = params['logger']
    guestname = params['guestname']
    bandwidth = params['bandwidth']
    flags = parse_flags(params, param_name='flags')
    logger.info("blockPull flags: %s, bandwidth: %s" % (flags, bandwidth))

    random_str = ''.join(get_rand_str())
    conn = libvirt.open()
    domobj = conn.lookupByName(guestname)
    path = get_path(domobj)

    snapshot_xml = ("<domainsnapshot><name>%s</name><memory snapshot='no' file=''/>"
                    "</domainsnapshot>" % random_str)

    try:
        domobj.snapshotCreateXML(snapshot_xml, 16)
        dom_xml = domobj.XMLDesc(0)
        tree = lxml.etree.fromstring(dom_xml)
        if len(tree.xpath("/domain/devices/disk/backingStore/@index")) != 0:
            logger.info("backing image exist.")

        logger.info("start block pull:")
        domobj.blockPull(path[0], int(bandwidth), flags)
        while(1):
            new_info = domobj.blockJobInfo(path[0], 0)
            if len(new_info) == 4 and new_info['type'] != 1:
                if new_info['type'] != 1:
                    logger.error("current block job type error: %s" % new_info['type'])
                    domobj.blockJobAbort(path[0])
                    snapobj = domobj.snapshotLookupByName(random_str, 0)
                    snapobj.delete(0)
                    return 1

                if flags == libvirt.VIR_DOMAIN_BLOCK_PULL_BANDWIDTH_BYTES:
                    if new_info['bandwidth'] != int(bandwidth) * 1024 * 1024:
                        logger.error("bandwidth error. blockJobInfo() "
                                     "bandwidth %s" % new_info['bandwidth'])
                        return 1
                else:
                    if new_info['bandwidth'] != int(bandwidth):
                        logger.error("bandwidth error. blockJobInfo() "
                                     "bandwidth %s" % new_info['bandwidth'])
                        return 1

            if len(new_info) == 0:
                logger.info("block pull complete.")
                break

            time.sleep(1)

        dom_xml = domobj.XMLDesc(0)
        tree = lxml.etree.fromstring(dom_xml)
        if len(tree.xpath("/domain/devices/disk/backingStore/@index")) != 0:
            logger.error("FAIL: block pull failed, backing image still exist.")
            return 1
        else:
            logger.info("PASS: block pull success, backing image is not exist.")
            del_img(tree.xpath("/domain/devices/disk/source/@file")[0])

    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0


def block_pull_clean(params):
    logger = params['logger']
    guestname = params['guestname']

    conn = libvirt.open()
    domobj = conn.lookupByName(guestname)
    dom_xml = domobj.XMLDesc(0)
    tree = lxml.etree.fromstring(dom_xml)
    img = tree.xpath("/domain/devices/disk/source/@file")[0]
    if os.path.exists(img):
        del_img(img)
