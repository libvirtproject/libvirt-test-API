#!/usr/bin/env python
# To test "virsh list" command

import os

import libvirt
from libvirt import libvirtError
from src import sharedmod

required_params = ('flags',)
optional_params = {}

CONFIG_DIR = '/etc/libvirt/qemu'
AUTOSTART_DIR = '/etc/libvirt/qemu/autostart'
RUNNING_DIR = '/var/run/libvirt/qemu'
SAVE_DIR = '/var/lib/libvirt/qemu/save'
SNAPSHOT_DIR = '/var/lib/libvirt/qemu/snapshot/'
CHECKPOINT_DIR = "/var/lib/libvirt/qemu/checkpoint/"

flag_list = {"default": 0,
             "active": libvirt.VIR_CONNECT_LIST_DOMAINS_ACTIVE,
             "persistent": libvirt.VIR_CONNECT_LIST_DOMAINS_PERSISTENT,
             "running": libvirt.VIR_CONNECT_LIST_DOMAINS_RUNNING,
             "paused": libvirt.VIR_CONNECT_LIST_DOMAINS_PAUSED,
             "shutoff": libvirt.VIR_CONNECT_LIST_DOMAINS_SHUTOFF,
             "managedsave": libvirt.VIR_CONNECT_LIST_DOMAINS_MANAGEDSAVE,
             "autostart": libvirt.VIR_CONNECT_LIST_DOMAINS_AUTOSTART,
             "snapshot": libvirt.VIR_CONNECT_LIST_DOMAINS_HAS_SNAPSHOT,
             "with_checkpoint": libvirt.VIR_CONNECT_LIST_DOMAINS_HAS_CHECKPOINT,
             "without_checkpoint": libvirt.VIR_CONNECT_LIST_DOMAINS_NO_CHECKPOINT}


def get_dir_entires(domain_dir, end_string):
    """get the domains list from the specified directory
    """
    guest_list = []
    end_length = len(end_string)
    try:
        dir_entries = os.listdir(domain_dir)
    except OSError as err:
        dir_entries = []

    if dir_entries == []:
        guest_list = []
    else:
        for entry in dir_entries:
            if not entry.endswith(end_string):
                continue
            else:
                if end_length == 0:
                    guest_list.append(entry)
                else:
                    guest = entry[:-end_length]
                    guest_list.append(guest)

    return guest_list


def check_domain_list(name_list, flag):
    """check the domains list
    """
    domains_config = get_dir_entires(CONFIG_DIR, ".xml")
    domains_active = get_dir_entires(RUNNING_DIR, ".xml")
    domains_autostart = get_dir_entires(AUTOSTART_DIR, ".xml")
    domains_save = get_dir_entires(SAVE_DIR, ".save")
    domains_checkpoint = get_dir_entires(CHECKPOINT_DIR, "")
    domains_inactive = list(set(domains_config) - set(domains_active))
    domain_list = []

    all_domains = list(set((domains_config + domains_active)))
    if len(domains_active) != conn.numOfDomains():
        logger.error("check the number of active domains failed")
        return 1
    else:
        logger.info("check the number of active domains succeeded")

    if len(domains_inactive) != conn.numOfDefinedDomains():
        logger.error("check the number of defined inactive domains failed")
        return 1
    else:
        logger.info("check the number of defined inactive domains succeeded")

    #Check the domain list with default flag
    if flag_list[flag] == 0:
        domain_list = all_domains
    #Check the domains list with active flag
    elif flag_list[flag] == libvirt.VIR_CONNECT_LIST_DOMAINS_ACTIVE:
        domain_list = domains_active
    #Check the domains list with defined flag
    elif flag_list[flag] == libvirt.VIR_CONNECT_LIST_DOMAINS_PERSISTENT:
        domain_list = domains_config
    #Check the domains list with running status
    elif flag_list[flag] == libvirt.VIR_CONNECT_LIST_DOMAINS_RUNNING:
        for name in all_domains:
            guest = conn.lookupByName(name)
            if guest.info()[0] == libvirt.VIR_DOMAIN_RUNNING:
                domain_list.append(guest.name())
    #Check the domains list with paused status
    elif flag_list[flag] == libvirt.VIR_CONNECT_LIST_DOMAINS_PAUSED:
        for name in all_domains:
            guest = conn.lookupByName(name)
            if guest.info()[0] == libvirt.VIR_DOMAIN_PAUSED:
                domain_list.append(guest.name())
    #Check the domains list with shutoff status
    elif flag_list[flag] == libvirt.VIR_CONNECT_LIST_DOMAINS_SHUTOFF:
        for name in all_domains:
            guest = conn.lookupByName(name)
            if guest.info()[0] == libvirt.VIR_DOMAIN_SHUTOFF:
                domain_list.append(guest.name())
    #Check the domains with a managed save image
    elif flag_list[flag] == libvirt.VIR_CONNECT_LIST_DOMAINS_MANAGEDSAVE:
        domain_list = domains_save
    #Check the domains list with autostart flag
    elif flag_list[flag] == libvirt.VIR_CONNECT_LIST_DOMAINS_AUTOSTART:
        domain_list = domains_autostart
    #Check the domains with sanpshot
    elif flag_list[flag] == libvirt.VIR_CONNECT_LIST_DOMAINS_HAS_SNAPSHOT:
        for guest in all_domains:
            if get_dir_entires(SNAPSHOT_DIR + guest, ".xml") == []:
                continue
            else:
                domain_list.append(guest)
    #Check the domains with checkpoint
    elif flag_list[flag] == libvirt.VIR_CONNECT_LIST_DOMAINS_HAS_CHECKPOINT:
        domain_list = domains_checkpoint
    #Check the domains without checkpoint
    elif flag_list[flag] == libvirt.VIR_CONNECT_LIST_DOMAINS_NO_CHECKPOINT:
        domain_list = list(set(all_domains) - set(domains_checkpoint))

    logger.info("check the %s domains list is %s" % (flag, domain_list))
    if sorted(domain_list) == sorted(name_list):
        return 0
    else:
        return 1


def domain_list(params):
    """get the domains list by API listAllDomains
    """
    global conn, logger
    conn = sharedmod.libvirtobj['conn']
    logger = params['logger']
    name_list = []

    flag = params['flags']
    logger.info("The given flag is %s" % flag)

    try:
        domain_obj_list = conn.listAllDomains(flag_list[flag])
        for domain in domain_obj_list:
            name_list.append(domain.name())
        logger.info("the domains list is %s" % name_list)

        if check_domain_list(name_list, flag) == 1:
            logger.error("get the domains list failed")
            return 1
        else:
            logger.info("get the domains list succeeded")

    except libvirtError as e:
        logger.error("API error message: %s" % e.get_error_message())
        return 1

    return 0
