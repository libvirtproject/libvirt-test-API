#!/usr/bin/evn python
# To test blockCopy()

import time

import libvirt
from libvirt import libvirtError

from utils import utils
from utils.utils import parse_flags, get_rand_str, del_file, get_xml_value

required_params = ('guestname', 'diskpath',)
optional_params = {'flags': None}

DEST_XML = "<disk><source file='%s'/></disk>"


def block_copy(params):
    """blockCopy test function
    """
    logger = params['logger']
    guestname = params['guestname']
    diskpath = params['diskpath']
    flags = parse_flags(params, param_name='flags')
    logger.info("blockCopy flags: %s, diskpath: %s" % (flags, diskpath))

    if "VIR_DOMAIN_BLOCK_COPY_TRANSIENT_JOB" in params.get('flags', None):
        if not utils.version_compare("libvirt-python", 3, 2, 0, logger):
            logger.info("Current libvirt-python don't support "
                        "flag VIR_DOMAIN_BLOCK_COPY_TRANSIENT_JOB.")
            return 0

    destxml = DEST_XML % diskpath
    logger.info("destxml: %s" % destxml)

    if not del_file(diskpath, logger):
        return 1

    if "VIR_DOMAIN_BLOCK_COPY_TRANSIENT_JOB" not in params.get('flags', None):
        cmd = "qemu-img create -f qcow2 %s 1G" % diskpath
        ret, out = utils.exec_cmd(cmd, shell=True)
        if ret:
            logger.error("create img failed. cmd: %s, out: %s" % (cmd, out))
            return 1

    random_str = ''.join(get_rand_str())
    conn = libvirt.open()
    domobj = conn.lookupByName(guestname)
    path = get_xml_value(domobj, "/domain/devices/disk/target/@dev")

    try:
        logger.info("start block copy:")
        domobj.blockCopy(path[0], destxml, None, flags)
        while(1):
            new_info = domobj.blockJobInfo(path[0], 0)
            if len(new_info) == 0:
                logger.info("block copy complete.")
                del_file(diskpath, logger)
                break

            if len(new_info) == 4 and new_info['type'] != 2:
                logger.error("block job type error: %s" % new_info['type'])
                domobj.blockJobAbort(path[0])
                del_file(diskpath, logger)
                return 1
            else:
                mirror_file = get_xml_value(domobj, "/domain/devices/disk/mirror/source/@file")
                job_type = get_xml_value(domobj, "/domain/devices/disk/mirror/@job")
                before_disk_img = get_xml_value(domobj, "/domain/devices/disk/source/@file")

                if "VIR_DOMAIN_BLOCK_COPY_SHALLOW" in params.get('flags', None):
                    dest_file = get_xml_value(domobj, "/domain/devices/disk/mirror/@file")
                    if dest_file[0] != diskpath:
                        logger.error("check dest file failed. dest: %s" % dest_file)
                        return 1
                    else:
                        logger.info("check dest file successful.")

                domobj.blockJobAbort(path[0])

                if "VIR_DOMAIN_BLOCK_COPY_TRANSIENT_JOB" in params.get('flags', None):
                    after_disk_img = get_xml_value(domobj, "/domain/devices/disk/source/@file")
                    if after_disk_img[0] != before_disk_img[0]:
                        logger.error("check disk img failed. disk img: %s" % after_disk_img)
                        return 1
                    else:
                        logger.info("check disk img successful.")

            time.sleep(1)

        if job_type[0] != "copy":
            logger.error("check job type failed. job: %s" % job_type)
            return 1
        else:
            logger.info("check job type successful.")

    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        domobj.blockJobAbort(path[0])
        return 1

    return 0
