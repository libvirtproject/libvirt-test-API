#!/usr/bin/env python
# To test "virsh domid" command

from src import sharedmod
from utils import process

required_params = ()
optional_params = {'guestname': ''}

VIRSH_DOMID = "virsh domid"
VIRSH_IDS = "virsh --quiet list |awk '{print $1}'"
VIRSH_DOMS = "virsh --quiet list |awk '{print $2}'"


def get_output(logger, command):
    """execute shell command
    """
    ret = process.run(command, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("executing " + "\"" + command + "\"" + " failed")
        logger.error(ret.stdout)
    return ret.exit_status, ret.stdout


def check_domain_exists(conn, guestname, logger):
    """ check if the domain exists, may or may not be active """
    guest_names = []
    ids = conn.listDomainsID()
    for id in ids:
        obj = conn.lookupByID(id)
        guest_names.append(obj.name())

    if guestname not in guest_names:
        logger.error("%s is not running or does not exist" % guestname)
        return False
    else:
        return True


def domain_id(params):
    """check virsh domid command
    """
    logger = params['logger']

    doms = []
    if 'guestname' in params:
        doms.append(params['guestname'])
    else:
        status, doms_ret = get_output(logger, VIRSH_DOMS)
        if not status:
            doms = doms_ret.split('\n')
        else:
            return 1

    if not doms:
        logger.info("no running guest available")
        return 1

    conn = sharedmod.libvirtobj['conn']

    for dom in doms:
        if not check_domain_exists(conn, dom, logger):
            return 1

    status, ids_ret = get_output(logger, VIRSH_IDS)
    if not status:
        ids_list = ids_ret.split('\n')
    else:
        return 1

    status, doms_ret = get_output(logger, VIRSH_DOMS)
    if not status:
        doms_list = doms_ret.split('\n')
    else:
        return 1

    domname_id = {}
    for dom in doms_list:
        index = doms_list.index(dom)
        domname_id[dom] = ids_list[index]

    for dom in doms:
        status, domid_ret = get_output(logger, VIRSH_DOMID + " %s" % dom)
        if status:
            return 1
        domid = domid_ret[:-1]
        if domname_id[dom] == domid:
            logger.info("domname %s corresponds to id %s" % (dom, domid))
        else:
            logger.error("domname %s fails to match id %s" % (dom, domid))
            return 1

    return 0
