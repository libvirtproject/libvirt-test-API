#!/usr/bin/evn python
# To test blockCommit()

import time

import libvirt
from libvirt import libvirtError

from utils.utils import parse_flags, get_rand_str, del_file, get_xml_value

required_params = ('guestname',)
optional_params = {'base': None,
                   'top': None,
                   'bandwidth': None,
                   'flags': None}


def block_commit(params):
    """blockCommit test function
    """
    logger = params['logger']
    guestname = params['guestname']
    base = params.get('base', None)
    top = params.get('top', None)
    bandwidth = params.get('bandwidth', 0)
    flags = parse_flags(params, param_name='flags')
    logger.info("blockCommit flags: %s, bandwidth: %s, base: %s, top: %s" %
                (flags, bandwidth, base, top))

    random_str = ''.join(get_rand_str())
    conn = libvirt.open()
    domobj = conn.lookupByName(guestname)
    path = get_xml_value(domobj, "/domain/devices/disk/target/@dev")

    img_file = get_xml_value(domobj, "/domain/devices/disk/source/@file")
    snapshot_xml = ("<domainsnapshot><name>%s</name><memory snapshot='no' file=''/>"
                    "</domainsnapshot>" % random_str)
    domobj.snapshotCreateXML(snapshot_xml, 16)

    try:
        logger.info("start block commit:")
        domobj.blockCommit(path[0], base, top, int(bandwidth), flags)
        new_info = domobj.blockJobInfo(path[0], 0)
        logger.info("job info: %s" % new_info)
        mirror_file = get_xml_value(domobj, "/domain/devices/disk/mirror/source/@file")
        job_type = get_xml_value(domobj, "/domain/devices/disk/mirror/@job")
        time.sleep(1)
        domobj.blockJobAbort(path[0], libvirt.VIR_DOMAIN_BLOCK_JOB_ABORT_PIVOT)
        if len(new_info) == 4 and new_info['type'] == 4:
            if "VIR_DOMAIN_BLOCK_COMMIT_SHALLOW" in params.get('flags', None):
                back_file = get_xml_value(domobj, "/domain/devices/disk/source/@file")
                if mirror_file[0] != back_file[0]:
                    logger.error("check back file failed.")
                    logger.error("back: %s, mirror: %s" % (back_file, mirror_file))
                    return 1
                else:
                    logger.info("check back file successful.")

            if "VIR_DOMAIN_BLOCK_COMMIT_BANDWIDTH_BYTES" in params.get('flags', None):
                if new_info['bandwidth'] * 1024 * 1024 == int(bandwidth):
                    logger.info("check bandwidth successful.")
                else:
                    logger.error("check bandwidth failed.")
                    return 1
            else:
                if new_info['bandwidth'] == int(bandwidth):
                    logger.info("check bandwidth successful.")
                else:
                    logger.error("check bandwidth failed.")
                    return 1

            if mirror_file[0] != img_file[0]:
                logger.error("check mirror file failed. mirror: %s" % mirror_file)
                return 1
            else:
                logger.info("check mirror file successful.")

            if job_type[0] != "active-commit":
                logger.error("check job type failed. job: %s" % job_type)
                return 1
            else:
                logger.info("check job type successful.")
        else:
            logger.error("check block job type or job info length error.")
            logger.error("job info: %s" % new_info)
            del_file(("/var/lib/libvirt/images/libvirt-test-api." + random_str), logger)
            return 1

        del_file(("/var/lib/libvirt/images/libvirt-test-api." + random_str), logger)

    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    return 0
