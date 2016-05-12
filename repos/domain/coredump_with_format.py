#!/usr/bin/env python
# test coreDumpWithFormat() API for libvirt

import os
import libvirt
import thread
import time

from libvirt import libvirtError
from src import sharedmod
from utils import utils

required_params = ('guestname', 'topath', 'dumpformat', 'flags',)
optional_params = {}

df = {"raw": libvirt.VIR_DOMAIN_CORE_DUMP_FORMAT_RAW,
      "zlib": libvirt.VIR_DOMAIN_CORE_DUMP_FORMAT_KDUMP_ZLIB,
      "lzo": libvirt.VIR_DOMAIN_CORE_DUMP_FORMAT_KDUMP_LZO,
      "snappy": libvirt.VIR_DOMAIN_CORE_DUMP_FORMAT_KDUMP_SNAPPY}

fg = {"mem": libvirt.VIR_DUMP_MEMORY_ONLY,
      "reset": libvirt.VIR_DUMP_RESET,
      "bypass": libvirt.VIR_DUMP_BYPASS_CACHE,
      "live": libvirt.VIR_DUMP_LIVE,
      "crash": libvirt.VIR_DUMP_CRASH}


def check_crash_command(logger):
    """
       check crash command on current OS
    """
    CMD = "which crash"
    status, output = utils.exec_cmd(CMD, shell=True)
    if status != 0:
        logger.info("Can not find crash command")
        return False
    else:
        return True


def check_dumpfile_type(topath, flags, logger):
    """
       check file type of generated file
    """
    GREP1 = "file %s |grep QEMU"
    GREP2 = "file %s |grep ELF"
    if flags < libvirt.VIR_DUMP_MEMORY_ONLY:
        status, output = utils.exec_cmd(GREP1 % topath, shell=True)
        if not status:
            logger.info("Check type of %s: Pass, %s" % (topath, output[0]))
            return True
        else:
            logger.info("Check type of %s: Fail, %s" % (topath, output[0]))
            return False
    elif flags >= libvirt.VIR_DUMP_MEMORY_ONLY:
        status, output = utils.exec_cmd(GREP2 % topath, shell=True)
        if not status:
            logger.info("Check type of %s: Pass, %s" % (topath, output[0]))
            return True
        else:
            logger.info("Check type of %s: Fail, %s" % (topath, output[0]))
            return False


def check_dump_file(*args):
    """
       check whether core dump file is generated
    """
    (core_file_path, logger) = args
    if os.access(core_file_path, os.R_OK):
        logger.info("Check core dump file %s: Pass" % core_file_path)
        return True
    else:
        logger.info("Check core dump file %s: Fail" % core_file_path)
        return False


def compare_compress_type(topath, dumpformat, logger):
    """
       check the compress type of file
    """
    GREP = "crash -d1 %s | grep \"COMPRESSED\""
    status, output = utils.exec_cmd(GREP % topath, shell=True)
    if not status:
        temp1 = output[0].strip()[:-1].split("_")[-1]
        if temp1 == dumpformat:
            logger.info("Check compress type %s of %s: Pass" % (temp1, topath))
            return True
        else:
            logger.info("Check compress type %s of %s: Fail, %s"
                        % (temp1, topath, dumpformat))
            return False
    else:
        logger.error("Can not get compress type from given file %s" % topath)
        return False


def check_domain_state(vmstate, flags, logger):
    """
       check domain state after doing coredump
    """
    if libvirt.VIR_DUMP_CRASH == libvirt.VIR_DUMP_CRASH & flags:
        if vmstate == [libvirt.VIR_DOMAIN_SHUTOFF,
                       libvirt.VIR_DOMAIN_SHUTOFF_CRASHED]:
            logger.info("domain status is %s,shut off (crashed): Pass"
                        % vmstate)
            return True
        else:
            logger.info("domain status is %s: Fail" % vmstate)
            return False
    else:
        if vmstate == [libvirt.VIR_DOMAIN_RUNNING,
                       libvirt.VIR_DOMAIN_RUNNING_UNPAUSED]:
            logger.info("domain status is %s,running (unpaused): Pass"
                        % vmstate)
            return True
        else:
            logger.info("domain status is %s: Fail" % vmstate)
            return False


def get_fileflags(topath, logger):
    """
       Get the file flags of coredump file
    """
    global fileflags
    CHECK_CMD = "lsof -w %s"
    GET_CMD = "cat /proc/$(lsof -w %s|awk '/libvirt_i/{print $2}')/fdinfo/1 \
            |grep flags|awk '{print $NF}'"
    utils.wait_for(lambda: os.path.exists(topath), 5)
    timeout = 10
    while True:
        (status, output) = utils.exec_cmd(CHECK_CMD % topath, shell=True)
        if status == 0 and len(output) > 0:
            break
        time.sleep(0.05)
        timeout -= 0.05
        if timeout < 0:
            logger.error("Timeout waiting for coredump file.")
            return 1
    (status, output) = utils.exec_cmd(GET_CMD % topath, shell=True)
    if status == 0 and len(output) == 1:
        logger.info("The flags of saved file %s " % output[0])
        fileflags = output[0][-5]
    else:
        logger.error("Fail to get the flags of saved file")
        return 1

    thread.exit_thread()


def check_fileflag(fileflags, logger):
    """
      Check the file flags of file if include O_DIRECT
    """
    if int(fileflags) == 4:
        logger.info("File flags include O_DIRECT: Pass")
        return True
    else:
        logger.error("File flags doesn't include O_DIRECT: Fail")
        return False


def coredump_with_format(params):
    """
       test APIs for coreDumpWithFormat in class virDomain
    """
    bypass_f = False
    logger = params['logger']
    domain_name = params['guestname']
    topath = params['topath']
    dumpformat = params['dumpformat']
    Udumpformat = dumpformat.upper()
    logger.info("The given dumpformat is %s" % dumpformat)
    if dumpformat == 'raw':
        dumpformat = df.get('raw')
    elif dumpformat == 'zlib':
        dumpformat = df.get('zlib')
    elif dumpformat == 'lzo':
        dumpformat = df.get('lzo')
    elif dumpformat == 'snappy':
        dumpformat = df.get('snappy')
    else:
        logger.info("Unknown flags")
        return 1

    flags = params['flags']
    logger.info("The flags are %s" % flags)
    flags_string = flags.split("|")
    flags = 0
    for flag in flags_string:
        if flag == 'mem':
            flags |= fg.get('mem')
        elif flag == 'reset':
            flags |= fg.get('reset')
        elif flag == 'bypass':
            flags |= fg.get('bypass')
            bypass_f = True
        elif flag == 'live':
            flags |= fg.get('live')
        elif flag == 'crash':
            flags |= fg.get('crash')
        else:
            logger.error("Unknown flags")
            return 1
    logger.info("The given flags is %d" % flags)
    try:
        conn = sharedmod.libvirtobj['conn']

        if conn.lookupByName(domain_name):
            dom = conn.lookupByName(domain_name)
        else:
            logger.error("Domain %s is not exist" % domain_name)
            return 1
        if not dom.isActive():
            logger.error("Domain %s is not running" % domain_name)
            return 1
        logger.info("The given path is %s" % topath)
        if bypass_f is True:
            thread.start_new_thread(get_fileflags, (topath, logger,))
        logger.info("Call the coreDumpWithFormat API")
        if dom.coreDumpWithFormat(topath, dumpformat, flags) == 0:

            if not check_dump_file(topath, logger):
                return 1
            if Udumpformat == "RAW":
                if not check_dumpfile_type(topath, flags, logger):
                    return 1
            else:
                if not check_crash_command(logger):
                    return 1
                if not compare_compress_type(topath, Udumpformat, logger):
                    return 1
            vmstate = dom.state()
            if not check_domain_state(vmstate, flags, logger):
                return 1
            if bypass_f is True:
                if not check_fileflag(fileflags, logger):
                    return 1

    except libvirtError as e:
        logger.error("API error message: %s" % e.message)
        return 1

    return 0


def coredump_with_format_clean(params):
    """clean testing environment"""

    logger = params['logger']
    topath = params['topath']
    CMD = "rm -rf %s"
    status, output = utils.exec_cmd(CMD % topath, shell=True)
    if status != 0:
        logger.info("Can not delete %s" % topath)
    else:
        logger.info("Deleted %s successfully" % topath)
