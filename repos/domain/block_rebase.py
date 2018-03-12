#!/usr/bin/evn python
# To test blockRebase()

import time
import tempfile

import libvirt
from libvirt import libvirtError

from utils import utils
from utils.utils import parse_flags, get_rand_str
from utils.utils import del_file, get_xml_value

required_params = ('guestname', 'flags')
optional_params = {'base': "",
                   'bandwidth': None,
                   'sourcehost': None,
                   'sourcepath': None}


def block_rebase(params):
    """domain blockRebase test function
    """
    logger = params['logger']
    guestname = params['guestname']
    bandwidth = params.get('bandwidth', None)
    base = params.get('base', "")
    sourcehost = params.get('sourcehost', None)
    sourcepath = params.get('sourcepath', None)
    flags = parse_flags(params, param_name='flags')

    logger.info("blockRebase flags: %s" % params.get("flags", None))
    logger.info("bandwidth: %s, base: %s" % (bandwidth, base))
    logger.info("sourcehost: %s, sourcepath: %s" % (sourcehost, sourcepath))

    if "VIR_DOMAIN_BLOCK_REBASE_COPY_DEV" in params.get("flags", None):
        mountpath = tempfile.mkdtemp()
        utils.setup_iscsi(sourcehost, sourcepath, mountpath, logger)
    else:
        if not del_file(base, logger):
            return 1

        if ("VIR_DOMAIN_BLOCK_REBASE_SHALLOW" in params.get("flags", None) or
                "VIR_DOMAIN_BLOCK_REBASE_REUSE_EXT" in params.get("flags", None)):
            cmd = "qemu-img create -f qcow2 %s 1G" % base
            ret, out = utils.exec_cmd(cmd, shell=True)
            if ret:
                logger.error("create img failed. cmd: %s, out: %s" % (cmd, out))
                return 1

    random_str = ''.join(get_rand_str())

    try:
        conn = libvirt.open()
        domobj = conn.lookupByName(guestname)
        path = get_xml_value(domobj, "/domain/devices/disk/target/@dev")

        logger.info("start block rebase:")
        if "VIR_DOMAIN_BLOCK_REBASE_RELATIVE" in params.get("flags", None):
            base = "block-rebase-relative"
            diskpath = get_xml_value(domobj, "/domain/devices/disk/source/@file")
            snapshot_xml = ("<domainsnapshot><name>%s</name></domainsnapshot>" % base)
            domobj.snapshotCreateXML(snapshot_xml, 16)
            snapshot_xml = ("<domainsnapshot><name>%s</name></domainsnapshot>" % random_str)
            domobj.snapshotCreateXML(snapshot_xml, 16)
            domobj.blockRebase(path[0], (diskpath[0] + '.' + base), 0, flags)

            while(1):
                new_info = domobj.blockJobInfo(path[0], 0)
                if len(new_info) == 4 and new_info['type'] != 1:
                    logger.error("job type error: %s" % new_info['type'])
                    domobj.blockJobAbort(path[0])
                    snapobj = domobj.snapshotLookupByName(random_str, 0)
                    snapobj.delete(0)
                    return 1

                if len(new_info) == 0:
                    logger.info("block rebase complete.")
                    break

                time.sleep(1)

            if len(get_xml_value(domobj, "/domain/devices/disk/backingStore/@index")) != 0:
                logger.error("FAIL: block rebase failed, backing image still exist.")
                return 1
            else:
                logger.info("PASS: block rebase success, backing image is not exist.")
                del_file(get_xml_value(domobj, "/domain/devices/disk/source/@file")[0])

        elif "VIR_DOMAIN_BLOCK_REBASE_COPY_RAW" in params.get('flags', None):
            domobj.blockRebase(path[0], base, 0, flags)
            new_info = domobj.blockJobInfo(path[0], 0)

            if len(new_info) == 4 and new_info['type'] == 2:
                job_type = get_xml_value(domobj, "/domain/devices/disk/mirror/@job")
                format_type = get_xml_value(domobj, "/domain/devices/disk/mirror/format/@type")
                logger.info("format type: %s" % format_type)
                del_file(base, logger)
                domobj.blockJobAbort(path[0])
                if format_type[0] != "raw":
                    logger.error("check format type failed. type: %s" % format_type)
                    return 1
                else:
                    logger.info("check format type successful.")

                if job_type[0] != "copy":
                    logger.error("check job type failed. job: %s" % job_type)
                    return 1
                else:
                    logger.info("check job type successful.")
            else:
                logger.error("block rebase info error: %s" % new_info)
                domobj.blockJobAbort(path[0])
                return 1

        elif "VIR_DOMAIN_BLOCK_REBASE_COPY_DEV" in params.get('flags', None):
            domobj.blockRebase(path[0], base, 0, flags)
            while(1):
                new_info = domobj.blockJobInfo(path[0], 0)
                if len(new_info) == 0:
                    logger.info("block rebase complete.")
                    utils.cleanup_iscsi(sourcepath, mountpath, logger)
                    del_file(mountpath, logger)
                    break

                if len(new_info) == 4 and new_info['type'] == 2:
                    job_type = get_xml_value(domobj, "/domain/devices/disk/mirror/@job")
                    dest_file = get_xml_value(domobj, "/domain/devices/disk/mirror/source/@dev")
                    logger.info("dest file: %s" % dest_file)
                    if dest_file[0] != base:
                        logger.error("check dest file failed. dest: %s" % dest_file)
                        return 1
                    else:
                        logger.info("check dest file successful.")
                    utils.cleanup_iscsi(sourcepath, mountpath, logger)
                else:
                    logger.error("block rebase info error: %s" % new_info)
                    domobj.blockJobAbort(path[0])
                    return 1

                time.sleep(1)

            if job_type[0] != "copy":
                logger.error("check job type failed. job: %s" % job_type)
                return 1
            else:
                logger.info("check job type successful.")

        elif "VIR_DOMAIN_BLOCK_REBASE_BANDWIDTH_BYTES" in params.get('flags', None):
            domobj.blockRebase(path[0], base, int(bandwidth), flags)
            new_info = domobj.blockJobInfo(path[0], 1)
            domobj.blockJobAbort(path[0])
            del_file(base, logger)

            if len(new_info) == 4 and new_info['type'] == 2:
                if new_info['bandwidth'] == int(bandwidth):
                    logger.info("Pass: check bandwidth successful.")
                else:
                    logger.error("Fail: check bandwidth failed.")
                    return 1
            else:
                logger.error("block rebase info error: %s" % new_info)
                return 1
        else:
            domobj.blockRebase(path[0], base, 0, flags)

            while(1):
                new_info = domobj.blockJobInfo(path[0], 0)
                if len(new_info) == 0:
                    logger.info("block rebase complete.")
                    break

                if len(new_info) == 4 and new_info['type'] == 2:
                    job_type = get_xml_value(domobj, "/domain/devices/disk/mirror/@job")

                    if "VIR_DOMAIN_BLOCK_REBASE_SHALLOW" in params.get('flags', None):
                        dest_file = get_xml_value(domobj, "/domain/devices/disk/mirror/@file")
                        logger.info("dest file: %s" % dest_file)
                        if dest_file[0] != base:
                            logger.error("check dest file failed. dest: %s" % dest_file)
                            return 1
                        else:
                            logger.info("check dest file successful.")
                else:
                    logger.error("block rebase info error: %s" % new_info)
                    domobj.blockJobAbort(path[0])
                    return 1

                time.sleep(1)

            if job_type[0] != "copy":
                logger.error("check job type failed. job: %s" % job_type)
                return 1
            else:
                logger.info("check job type successful.")

    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    return 0


def block_rebase_clean(params):
    logger = params['logger']
    base = params.get('base', "")
    sourcepath = params.get('sourcepath', None)

    if "VIR_DOMAIN_BLOCK_REBASE_RELATIVE" in params.get('flags', None):
        cmd = "rm -f /var/lib/libvirt/images/libvirt-test-api.*"
        ret, out = utils.exec_cmd(cmd, shell=True)
        if ret != 0:
            logger.error("clean env failed.")
    elif "VIR_DOMAIN_BLOCK_REBASE_COPY_DEV" in params.get('flags', None):
        utils.cleanup_iscsi(sourcepath, base, logger)
    else:
        del_file(base, logger)
