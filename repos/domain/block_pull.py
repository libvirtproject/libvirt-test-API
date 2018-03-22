#!/usr/bin/evn python
# To test blockpull()

import time

import libvirt
from libvirt import libvirtError

from utils.utils import parse_flags, get_rand_str, del_file, get_xml_value

required_params = ('guestname', 'bandwidth', 'flags',)
optional_params = {}


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
    path = get_xml_value(domobj, "/domain/devices/disk/target/@dev")

    snapshot_xml = ("<domainsnapshot><name>%s</name><memory snapshot='no' file=''/>"
                    "</domainsnapshot>" % random_str)

    try:
        domobj.snapshotCreateXML(snapshot_xml, 16)

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
                        logger.error("bandwidth %s error." % new_info['bandwidth'])
                        return 1
                else:
                    if new_info['bandwidth'] != int(bandwidth):
                        logger.error("bandwidth %s error." % new_info['bandwidth'])
                        return 1

            if len(new_info) == 0:
                logger.info("block pull complete.")
                break

            time.sleep(1)

        if len(get_xml_value(domobj, "/domain/devices/disk/backingStore/@index")) != 0:
            logger.error("FAIL: block pull failed, backing image still exist.")
            return 1
        else:
            logger.info("PASS: block pull success, backing image is not exist.")
            img = get_xml_value(domobj, "/domain/devices/disk/source/@file")
            del_file(img[0], logger)

    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    return 0


def block_pull_clean(params):
    logger = params['logger']
    guestname = params['guestname']

    conn = libvirt.open()
    domobj = conn.lookupByName(guestname)
    img = get_xml_value(domobj, "/domain/devices/disk/source/@file")
    del_file(img[0], logger)
