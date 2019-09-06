#!/usr/bin/evn python

import os

import libvirt
from libvirt import libvirtError
from src import sharedmod
from utils import utils

required_params = ('guestname',)
optional_params = {'flags': 'none',
                   'xml': 'xmls/nvram.xml',
                   'virt_type': 'kvm',
                   }

nvram_path = "/var/lib/libvirt/qemu/nvram/test_VARS.fd"


def parse_flags(logger, flags):
    logger.info('undefine with flags :%s' % flags)
    if flags == 'none':
        return None
    ret = 0
    for flag in flags.split('|'):
        if flag == 'managed_save':
            ret = ret | libvirt.VIR_DOMAIN_UNDEFINE_MANAGED_SAVE
        elif flag == 'snapshots_metadata':
            ret = ret | libvirt.VIR_DOMAIN_UNDEFINE_SNAPSHOTS_METADATA
        elif flag == 'nvram':
            ret = ret | libvirt.VIR_DOMAIN_UNDEFINE_NVRAM
        elif flag == 'keep_nvram':
            if utils.version_compare("libvirt-python", 2, 5, 0, logger):
                ret = ret | libvirt.VIR_DOMAIN_UNDEFINE_KEEP_NVRAM
            else:
                logger.info("Current libvirt-python don't support 'keep_nvram' flag.")
                return -2
        elif flag == 'checkpoints_metadata':
            if utils.version_compare("libvirt-python", 5, 6, 0, logger):
                ret = ret | libvirt.VIR_DOMAIN_UNDEFINE_CHECKPOINTS_METADATA
            else:
                logger.info("Current libvirt-python don't support 'checkpoints-metadata' flag.")
                return -2
        else:
            logger.error('illegal flags')
            return -1
    return ret


def check_domain_state(conn, guestname, logger):
    """ if a guest with the same name exists, remove it """
    running_guests = []
    ids = conn.listDomainsID()
    for id in ids:
        obj = conn.lookupByID(id)
        running_guests.append(obj.name())

    if guestname in running_guests:
        logger.info("A guest with the same name %s is running!" % guestname)
        logger.info("destroy it...")
        domobj = conn.lookupByName(guestname)
        domobj.destroy()

    defined_guests = conn.listDefinedDomains()

    if guestname in defined_guests:
        logger.info("undefine the guest with the same name %s" % guestname)
        domobj = conn.lookupByName(guestname)
        domobj.undefine()

    return 0


def check_undefine_domain(flags, guestname, logger, virt_type='kvm'):
    """Check undefine domain result, if undefine domain is successful,
       guestname.xml will don't exist under /etc/libvirt/qemu/
    """
    for flag in flags.split('|'):
        if flag == "nvram":
            if os.access(nvram_path, os.R_OK):
                logger.error("for nvram flags, %s still exist." % nvram_path)
                return False
        if flag == "keep_nvram":
            if utils.version_compare("libvirt-python", 2, 5, 0, logger):
                if not os.access(nvram_path, os.R_OK):
                    logger.error("for keep_nvram flags, %s don't exist." % nvram_path)
                    return False

    if "lxc" in virt_type:
        path = "/etc/libvirt/lxc/%s.xml" % guestname
    else:
        path = "/etc/libvirt/qemu/%s.xml" % guestname

    if not os.access(path, os.R_OK):
        return True
    else:
        return False


def undefine(params):
    """Undefine a domain"""
    logger = params['logger']
    guestname = params['guestname']
    virt_type = params.get('virt_type', 'kvm')
    if "lxc" in virt_type:
        conn = libvirt.open("lxc:///")
    else:
        conn = libvirt.open()
    flags = params.get('flags', 'none')
    libvirt_flags = parse_flags(logger, flags)

    if libvirt_flags == -1:
        return 1
    elif libvirt_flags == -2:
        return 0

    for flag in flags.split('|'):
        if flag == "nvram" or flag == "keep_nvram":
            if not os.access(nvram_path, os.R_OK):
                logger.error("%s don't exist." % nvram_path)
                return 1

    domobj = conn.lookupByName(guestname)

    try:
        if libvirt_flags is None:
            domobj.undefine()
        else:
            domobj.undefineFlags(libvirt_flags)

        if check_undefine_domain(flags, guestname, logger, virt_type):
            logger.info("undefine the domain is successful")
        else:
            logger.error("fail to check domain undefine")
            return 1
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    return 0


def undefine_clean(params):
    flags = params.get('flags', 'none')
    guestname = params['guestname']
    logger = params['logger']
    conn = libvirt.open(None)

    for flag in flags.split('|'):
        if flag == "keep_nvram":
            if not utils.version_compare("libvirt-python", 2, 5, 0, logger):
                domobj = conn.lookupByName(guestname)
                domobj.undefineFlags(libvirt.VIR_DOMAIN_UNDEFINE_NVRAM)
