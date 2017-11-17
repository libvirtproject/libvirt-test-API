#!/usr/bin/env python

from utils.utils import get_disk_path, exec_cmd, version_compare


def check_domain_image(domobj, guestname, format_required, logger):
    """ Check the format of disk image """
    dom_xml = domobj.XMLDesc(0)
    disk_path = get_disk_path(dom_xml)
    if version_compare("libvirt-python", 3, 8, 0, logger):
        qemu_img_format = "qemu-img info -U %s |grep format |awk -F': ' '{print $2}'"
    else:
        qemu_img_format = "qemu-img info %s |grep format |awk -F': ' '{print $2}'"

    (status, output) = exec_cmd(qemu_img_format % disk_path,
                                      shell=True)
    if status:
        logger.error('Executing "' + qemu_img_format % guestname + '" failed"')
        logger.error(output)
        return False
    else:
        img_format = output[0]
        if img_format == format_required:
            logger.info("The format of domain image is " + format_required)
            return True
        else:
            logger.error("%s has a disk %s with type %s, should be %s" %
                         (guestname, disk_path, img_format, format_required))
            return False


def convert_flags(flags, flag_dict, logger):
    """ Bitwise-OR of flags in conf and convert them to the readable flags """

    flaglist = []
    flagstr = ""
    logger.info("The given flags are %s " % flags)
    if '|' not in flags:
        flagn = int(flags)
        flaglist.append(flagn)
    else:
        # bitwise-OR of flags of create-snapshot
        flaglist = flags.split('|')
        flagn = 0
        for flag in flaglist:
            flagn |= int(flag)

    # Convert the flags in conf file to readable flag
    for flag_key in flaglist:
        if flag_dict.has_key(int(flag_key)):
            flagstr += flag_dict.get(int(flag_key))
    logger.info("Converted flags:" + flagstr if flagstr != "" else "no flag")

    return (flaglist, flagn)
