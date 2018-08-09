#!/usr/bin/env python

import json
import time

import libvirt
from libvirt import libvirtError
from utils import utils, process
from src import sharedmod
from repos.domain import domain_common

required_params = ('transport',
                   'target_machine',
                   'username',
                   'password',
                   'guestname',
                   'prestate',
                   'poststate',
                   'presrcconfig',
                   'postsrcconfig',
                   'predstconfig',
                   'postdstconfig',
                   'flags',)
optional_params = {'auth_tcp': '',
                   'xml': None,
                   'migrate_uri': None,
                   'params_list': None,
                   'diskpath': '/var/lib/libvirt/migrate/libvirt-test-api'}


def get_state(state):
    dom_state = ''
    if state == libvirt.VIR_DOMAIN_NOSTATE:
        dom_state = 'nostate'
    elif state == libvirt.VIR_DOMAIN_RUNNING:
        dom_state = 'running'
    elif state == libvirt.VIR_DOMAIN_BLOCKED:
        dom_state = 'blocked'
    elif state == libvirt.VIR_DOMAIN_PAUSED:
        dom_state = 'paused'
    elif state == libvirt.VIR_DOMAIN_SHUTDOWN:
        dom_state = 'shutdown'
    elif state == libvirt.VIR_DOMAIN_SHUTOFF:
        dom_state = 'shutoff'
    elif state == libvirt.VIR_DOMAIN_CRASHED:
        dom_state = 'crashed'
    else:
        dom_state = 'no sure'
    return dom_state


def exec_command(logger, command, flag):
    """execute shell command
    """
    ret = process.run(command, shell=True, ignore_status=True)
    if not flag and ret.exit_status:
        logger.error("executing " + "\"" + command + "\"" + " failed")
        logger.error(ret.stdout)
    return ret.exit_status, ret.stdout


def env_clean(srcconn, dstconn, target_machine, guestname, logger):
    logger.info("destroy and undefine %s on both side if it exsits", guestname)
    exec_command(logger, "virsh destroy %s" % guestname, 1)
    exec_command(logger, "virsh undefine %s" % guestname, 1)
    REMOTE_DESTROY = "ssh %s \"virsh destroy %s\"" % (
        target_machine, guestname)
    exec_command(logger, REMOTE_DESTROY, 1)
    REMOTE_UNDEFINE = "ssh %s \"virsh undefine %s\"" % (
        target_machine, guestname)
    exec_command(logger, REMOTE_UNDEFINE, 1)

    dstconn.close()
    logger.info("close remote hypervisor connection")

    REMOVE_SSH = "ssh %s \"rm -rf /root/.ssh/*\"" % (target_machine)
    logger.info("remove ssh key on remote machine")
    status, ret = exec_command(logger, REMOVE_SSH, 0)
    if status:
        logger.error("failed to remove ssh key")

    REMOVE_LOCAL_SSH = "rm -rf /root/.ssh/*"
    logger.info("remove local ssh key")
    status, ret = exec_command(logger, REMOVE_LOCAL_SSH, 0)
    if status:
        logger.error("failed to remove local ssh key")


def check_virtlogd(target_machine, username, password, logger):
    logger.info("check local and remote virtlogd status")
    logger.info("bug 1325503 : virtlogd is not started/enabled on fresh libvirt install")

    check_cmd = "systemctl status virtlogd.socket | grep \"inactive (dead)\""
    logger.debug("cmd : %s" % check_cmd)
    ret, out = utils.remote_exec_pexpect(target_machine, username,
                                         password, check_cmd)
    logger.debug("ret = %s, out = %s" % (ret, out))
    if "inactive (dead)" in out:
        logger.info("start remote virtlogd.socket")
        start_cmd = "systemctl start virtlogd.socket"
        ret, output = utils.remote_exec_pexpect(target_machine, username,
                                                password, start_cmd)
        if ret:
            logger.error("failed to start remote virtlogd.socket service, %s" % ret)
            logger.error("output: %s" % output)
            return 1

    ret, out = utils.exec_cmd(check_cmd, shell=True)
    logger.debug("ret = %s, out = %s" % (ret, out))
    if ret == 3:
        logger.info("start local virtlogd.socket")
        start_cmd = "systemctl start virtlogd.socket"
        ret, output = utils.exec_cmd(start_cmd, shell=True)
        if ret:
            logger.error("failed to start local virtlogd.socket service, %s" % ret)
            logger.error("output: %s" % output)
            return 1

    logger.info("done the virtlogd.socket service start job")
    return 0


def guest_clean(conn, guestname, logger):
    running_guests = []
    ids = conn.listDomainsID()
    for id in ids:
        obj = conn.lookupByID(id)
        running_guests.append(obj.name())

    if guestname in running_guests:
        logger.info("destroy %s" % guestname)
        domobj = conn.lookupByName(guestname)
        domobj.destroy()

    defined_guests = conn.listDefinedDomains()

    if guestname in defined_guests:
        logger.info("undefine %s" % guestname)
        domobj = conn.lookupByName(guestname)
        domobj.undefine()

    return 0


def migrate(params):
    """ migrate a guest back and forth between two machines"""
    logger = params['logger']

    transport = params['transport']
    target_machine = params['target_machine']
    username = params['username']
    password = params['password']
    guestname = params['guestname']
    poststate = params['poststate']
    presrcconfig = params['presrcconfig']
    postsrcconfig = params['postsrcconfig']
    predstconfig = params['predstconfig']
    postdstconfig = params['postdstconfig']
    flags = params['flags']

    diskpath = params.get('diskpath', '/var/lib/libvirt/migrate/libvirt-test-api')
    auth_tcp = params.get('auth_tcp', '')
    domxml = params.get('xml', None)
    migrate_uri = params.get('migrate_uri', None)
    if not utils.version_compare("libvirt", 3, 2, 0, logger):
        if migrate_uri is not None:
            logger.info("Current libvirt don't support migrate_uri.")
            conn = libvirt.open(None)
            time.sleep(10)
            guest_clean(conn, guestname, logger)
            return 0

    tmp_list = params.get('params_list', None)
    params_list = None
    if tmp_list:
        params_list = json.loads(tmp_list)

    logger.info("the flags is %s" % flags)
    flags_string = flags.split("|")

    migflags = 0
    for flag in flags_string:
        if flag == '0':
            migflags |= 0
        elif flag == 'peer2peer':
            migflags |= libvirt.VIR_MIGRATE_PEER2PEER
        elif flag == 'tunnelled':
            migflags |= libvirt.VIR_MIGRATE_TUNNELLED
        elif flag == 'live':
            migflags |= libvirt.VIR_MIGRATE_LIVE
        elif flag == 'persist_dest':
            migflags |= libvirt.VIR_MIGRATE_PERSIST_DEST
        elif flag == 'undefine_source':
            migflags |= libvirt.VIR_MIGRATE_UNDEFINE_SOURCE
        elif flag == 'paused':
            migflags |= libvirt.VIR_MIGRATE_PAUSED
        else:
            logger.error("unknown flag")
            return 1

    # To avoid error: "Unsafe migration: Migration without "
    # "shared storage is unsafe"
    #migflags |= libvirt.VIR_MIGRATE_UNSAFE

    #generate ssh key pair
    ret = domain_common.ssh_keygen(logger)
    if ret:
        logger.error("failed to generate RSA key")
        return 1
    #setup ssh tunnel with target machine
    ret = domain_common.ssh_tunnel(target_machine, username, password, logger)
    if ret:
        logger.error(
            "faild to setup ssh tunnel with target machine %s" %
            target_machine)
        return 1

    process.run("ssh-add", shell=True, ignore_status=True)
    check_virtlogd(target_machine, username, password, logger)

    dsturi = "qemu+%s://%s/system" % (transport, target_machine)

    # Connect to local hypervisor connection URI
    srcconn = sharedmod.libvirtobj['conn']

    if auth_tcp == '':
        dstconn = libvirt.open(dsturi)
    elif auth_tcp == 'sasl':
        user_data = [username, password]
        auth = [[libvirt.VIR_CRED_AUTHNAME, libvirt.VIR_CRED_PASSPHRASE],
                domain_common.request_credentials, user_data]
        dstconn = libvirt.openAuth(dsturi, auth, 0)

    srcdom = srcconn.lookupByName(guestname)

    if predstconfig == "true":
        guest_names = dstconn.listDefinedDomains()
        if guestname in guest_names:
            logger.info("Dst VM exists")
        else:
            logger.error(
                "Dst VM missing config, should define VM on Dst first")
            env_clean(srcconn, dstconn, target_machine, guestname, logger)
            return 1

    try:
        ## Add for test
        logger.info("xml for migration: %s\n\n" % srcdom.XMLDesc(libvirt.VIR_DOMAIN_XML_MIGRATABLE))
        logger.info("xml: %s\n\n" % srcdom.XMLDesc())
        ## End for test
        if(migflags & libvirt.VIR_MIGRATE_PEER2PEER):
            if domxml is None:
                logger.info("use migrateToURI() to migrate")
                srcdom.migrateToURI(dsturi, migflags, None, 0)
            else:
                domxml = domxml.replace('GUESTNAME', guestname)
                domxml = domxml.replace('UUID', srcdom.UUIDString())
                domxml = domxml.replace('DISKPATH', diskpath)
                if params_list:
                    if migrate_uri:
                        params_list['migrate_uri'] = migrate_uri
                    if domxml:
                        params_list['destination_xml'] = domxml
                    logger.info("use migrateToURI3() to migrate")
                    srcdom.migrateToURI3(dsturi, params_list, migflags)
                else:
                    logger.info("migrate_uri: %s" % migrate_uri)
                    logger.info("use migrateToURI2() to migrate")
                    srcdom.migrateToURI2(dsturi, migrate_uri, domxml, migflags, None, 0)
        else:
            logger.info("use migrate() to migrate")
            srcdom.migrate(dstconn, migflags, None, None, 0)
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("Migration Failed")
        env_clean(srcconn, dstconn, target_machine, guestname, logger)
        return 1

    if postsrcconfig == "true":
        if srcdom.isActive():
            logger.error("Source VM is still active")
            env_clean(srcconn, dstconn, target_machine, guestname, logger)
            return 1
        if not srcdom.isPersistent():
            logger.error("Source VM missing config")
            env_clean(srcconn, dstconn, target_machine, guestname, logger)
            return 1
    else:
        guest_names = []
        ids = srcconn.listDomainsID()
        for id in ids:
            obj = srcconn.lookupByID(id)
            guest_names.append(obj.name())
        guest_names += srcconn.listDefinedDomains()

        if guestname in guest_names:
            logger.error("Source VM still exists")
            env_clean(srcconn, dstconn, target_machine, guestname, logger)
            return 1

    dstdom = dstconn.lookupByName(guestname)
    if not dstdom.isActive():
        logger.error("Dst VM is not active")
        env_clean(srcconn, dstconn, target_machine, guestname, logger)
        return 1

    if postdstconfig == "true":
        if not dstdom.isPersistent():
            logger.error("Dst VM missing config")
            env_clean(srcconn, dstconn, target_machine, guestname, logger)
            return 1

    dstdom_state = dstdom.info()[0]
    if get_state(dstdom_state) != poststate:
        logger.error(
            "Dst VM wrong state %s, should be %s",
            get_state(dstdom_state),
            poststate)
        env_clean(srcconn, dstconn, target_machine, guestname, logger)
        return 1

    logger.info("Migration PASS")
    env_clean(srcconn, dstconn, target_machine, guestname, logger)
    return 0
