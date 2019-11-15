#!/usr/bin/env python

import os
import shutil
import time

import libvirt
from libvirt import libvirtError

from utils import utils
from repos.domain import domain_common
from repos.remoteAccess import remote_common

required_params = ('listen_tls',
                   'auth_tls',
                   'target_machine',
                   'username',
                   'password',)
optional_params = {}

CERTTOOL = "/usr/bin/certtool"
CP = "/bin/cp"
MKDIR = "/bin/mkdir"
CA_FOLDER = "/etc/pki/qemu"
SASLPASSWD2 = "/usr/sbin/saslpasswd2"
LIBVIRTD_CONF = "/etc/libvirt/libvirtd.conf"
SYSCONFIG_LIBVIRTD = "/etc/sysconfig/libvirtd"

TEMP_TLS_FOLDER = "/tmp/libvirt_test_API_tls_2"
CAKEY = os.path.join(TEMP_TLS_FOLDER, 'ca-key.pem')
CACERT = os.path.join(TEMP_TLS_FOLDER, 'ca-cert.pem')
SERVERKEY = os.path.join(TEMP_TLS_FOLDER, 'server-key.pem')
SERVERCERT = os.path.join(TEMP_TLS_FOLDER, 'server-cert.pem')
CLIENTKEY = os.path.join(TEMP_TLS_FOLDER, 'client-key.pem')
CLIENTCERT = os.path.join(TEMP_TLS_FOLDER, 'client-cert.pem')


def CA_setting_up(target_machine, logger):
    """ setting up a Certificate Authority """
    # Create a private key for CA
    logger.info("generate CA certificates")

    cakey_fd = open(CAKEY, 'w')
    ret, out = utils.exec_cmd([CERTTOOL, '--generate-privkey'], outfile=cakey_fd)
    cakey_fd.close()
    if ret != 0:
        logger.error("failed to create CA private key")
        return 1

    # ca.info file
    cainfo = os.path.join(TEMP_TLS_FOLDER, 'ca.info')
    cainfo_fd = open(cainfo, 'w')
    cainfo_str = ("cn = %s\n"
                  "ca\n"
                  "cert_signing_key\n" % target_machine)

    cainfo_fd.write(cainfo_str)
    cainfo_fd.close()

    # Generate cacert.pem
    cacert_args = [CERTTOOL, '--generate-self-signed', '--load-privkey', CAKEY, '--template', cainfo]
    cacert_fd = open(CACERT, 'w')
    ret, out = utils.exec_cmd(cacert_args, outfile=cacert_fd)
    cacert_fd.close()
    if ret != 0:
        logger.error("failed to create cacert.pem")
        return 1

    logger.info("done the CA certificates job")
    return 0


def tls_server_cert(target_machine, logger):
    """ generating server certificates """
    # Create tls server key
    logger.info("generate server certificates")

    serverkey_fd = open(SERVERKEY, 'w')
    ret, out = utils.exec_cmd([CERTTOOL, '--generate-privkey'], outfile=serverkey_fd)
    serverkey_fd.close()
    if ret != 0:
        logger.error("failed to create server key")
        return 1

    # server.info
    serverinfo = os.path.join(TEMP_TLS_FOLDER, 'server.info')
    serverinfo_fd = open(serverinfo, 'w')
    serverinfo_str = ("organization = Red Hat\n"
                      "cn = %s\n"
                      "tls_www_server\n"
                      "encryption_key\n"
                      "signing_key\n" % target_machine)

    serverinfo_fd.write(serverinfo_str)
    serverinfo_fd.close()

    # Generate servercert.pem
    servercert_args = [CERTTOOL,
                       '--generate-certificate',
                       '--load-privkey', SERVERKEY,
                       '--load-ca-certificate', CACERT,
                       '--load-ca-privkey', CAKEY,
                       '--template', serverinfo
                       ]
    servercert_fd = open(SERVERCERT, 'w')
    ret, out = utils.exec_cmd(servercert_args, outfile=servercert_fd)
    servercert_fd.close()
    if ret != 0:
        logger.error("failed to create servercert.pem")
        return 1

    logger.info("done the server certificates job")
    return 0


def tls_client_cert(local_machine, logger):
    """ generating client certificates """
    # Create tls client key
    logger.info("generate client certificates")

    clientkey_fd = open(CLIENTKEY, 'w')
    ret, out = utils.exec_cmd([CERTTOOL, '--generate-privkey'], outfile=clientkey_fd)
    clientkey_fd.close()
    if ret != 0:
        logger.error("failed to create client key")
        return 1

    # client.info
    clientinfo = os.path.join(TEMP_TLS_FOLDER, 'client.info')
    clientinfo_fd = open(clientinfo, 'w')
    clientinfo_str = ("country = GB\n"
                      "state = London\n"
                      "locality = London\n"
                      "organization = Red Hat\n"
                      "cn = %s\n"
                      "tls_www_client\n"
                      "encryption_key\n"
                      "signing_key\n" % local_machine)

    clientinfo_fd.write(clientinfo_str)
    clientinfo_fd.close()

    # Generate clientcert.pem
    clientcert_args = [CERTTOOL,
                       '--generate-certificate',
                       '--load-privkey', CLIENTKEY,
                       '--load-ca-certificate', CACERT,
                       '--load-ca-privkey', CAKEY,
                       '--template', clientinfo,
                       ]

    clientcert_fd = open(CLIENTCERT, 'w')
    ret, out = utils.exec_cmd(clientcert_args, outfile=clientcert_fd)
    clientcert_fd.close()
    if ret != 0:
        logger.error("failed to create client certificates")
        return 1

    logger.info("done the client certificates job")
    return 0


def deliver_cert(target_machine, username, password, logger):
    """ deliver CA, server and client certificates """
    # mkdir /etc/pki/qemu on remote host
    ca_folder_cmd = "mkdir -p %s" % CA_FOLDER
    ret, output = utils.remote_exec_pexpect(target_machine, username, password, ca_folder_cmd)
    if ret:
        logger.error("failed to make /etc/pki/qemu on %s" % target_machine)
        return 1

    # mkdir /etc/pki/qemu on local host
    ca_folder_cmd_local = [MKDIR, '-p', CA_FOLDER]
    ret, out = utils.exec_cmd(ca_folder_cmd_local)
    if ret:
        logger.error("failed to make %s on local" % CA_FOLDER)
        return 1

    # transmit ca-cert.pem to remote host
    logger.info("deliver CA, server and client certificates to both local and remote server")
    ret = utils.scp_file(target_machine, username, password, CA_FOLDER, CACERT)
    if ret:
        logger.error("scp ca-cert.pem to %s error" % target_machine)
        return 1

    # transmit ca-key.pem to remote host
    ret = utils.scp_file(target_machine, username, password, CA_FOLDER, CAKEY)
    if ret:
        logger.error("scp ca-key.pem to %s error" % target_machine)
        return 1

    # copy ca-cert.pem to local CA folder
    cacert_cp = [CP, '-f', CACERT, CA_FOLDER]
    ret, out = utils.exec_cmd(cacert_cp)
    if ret:
        logger.error("copying ca-cert.pem to %s error" % CA_FOLDER)
        return 1

    # copy ca-key.pem to local CA folder
    cakey_cp = [CP, '-f', CAKEY, CA_FOLDER]
    ret, out = utils.exec_cmd(cakey_cp)
    if ret:
        logger.error("copying ca-key.pem to %s error" % CA_FOLDER)
        return 1

    # transmit server-key.pem to remote host
    ret = utils.scp_file(target_machine, username, password, CA_FOLDER, SERVERKEY)
    if ret:
        logger.error("failed to scp server-key.pem to %s" % target_machine)
        return 1

    # transmit server-cert.pem to remote host
    ret = utils.scp_file(target_machine, username, password, CA_FOLDER, SERVERCERT)
    if ret:
        logger.error("failed to scp server-cert.pem to %s" % target_machine)
        return 1

    # copy client-key.pem to local folder
    clientkey_cp = [CP, '-f', CLIENTKEY, CA_FOLDER]
    ret, out = utils.exec_cmd(clientkey_cp)
    if ret:
        logger.error("failed to copy client-key.pem to %s" % CA_FOLDER)
        return 1

    # copy client-cert.pem to local folder
    clientcert_cp = [CP, '-f', CLIENTCERT, CA_FOLDER]
    ret, out = utils.exec_cmd(clientcert_cp)
    if ret:
        logger.error("failed to copy client-cert.pem to %s" % CA_FOLDER)
        return 1

    logger.info("done to delivery")
    return 0


def sasl_user_add(target_machine, username, password, logger):
    """ execute saslpasswd2 to add sasl user """
    logger.info("add sasl user on server side")
    saslpasswd2_add = "echo %s | %s -a libvirt %s" % (password, SASLPASSWD2, username)
    ret, output = utils.remote_exec_pexpect(target_machine, username,
                                            password, saslpasswd2_add)
    if ret:
        logger.error("failed to add sasl user")
        return 1

    return 0


def tls_libvirtd_set(target_machine, username, password,
                     listen_tls, auth_tls, logger):
    """ configure libvirtd.conf on tls server """
    logger.info("Setting libvirtd.conf on tls server")
    # set listen_tcp
    logger.info("Set 'listen_tcp = 0' in %s" % LIBVIRTD_CONF)
    listen_tcp_disable = "echo \"listen_tcp = 0\" >> %s" % LIBVIRTD_CONF
    ret, output = utils.remote_exec_pexpect(target_machine, username,
                                            password, listen_tcp_disable)
    if ret:
        logger.error("Failed to set 'listen_tcp = 0' in %s" % LIBVIRTD_CONF)
        return 1

    # set listen_tls
    if listen_tls == 'enable':
        logger.info("Set 'listen_tls = 1' in %s" % LIBVIRTD_CONF)
        listen_tls_enable = "echo \"listen_tls = 1\" >> %s" % LIBVIRTD_CONF
        ret, output = utils.remote_exec_pexpect(target_machine, username,
                                                password, listen_tls_enable)
        if ret:
            logger.error("Failed to set 'listen_tls = 1' in %s" % LIBVIRTD_CONF)
            return 1
    elif listen_tls == 'disable':
        logger.info("Set 'listen_tls = 0' in %s" % LIBVIRTD_CONF)
        listen_tls_set = "echo 'listen_tls = 0' >> %s" % LIBVIRTD_CONF
        ret, output = utils.remote_exec_pexpect(target_machine, username,
                                                password, listen_tls_set)
        if ret:
            logger.error("Failed to set 'listen_tls' in %s" % LIBVIRTD_CONF)
            return 1

    # set auth_tls
    logger.info("Set 'auth_tls = %s' in %s" % (auth_tls, LIBVIRTD_CONF))
    auth_tls_set = 'echo "auth_tls = \\\"%s\\\"" >> %s' % (auth_tls, LIBVIRTD_CONF)
    ret, output = utils.remote_exec_pexpect(target_machine, username,
                                            password, auth_tls_set)
    if ret:
        logger.error("Failed to set 'auth_tls' in %s" % LIBVIRTD_CONF)
        return 1

    # Restart remote libvirtd
    if remote_common.restart_remote_libvirtd(target_machine, username,
                                             password, logger, 'tls'):
        return 1

    time.sleep(3)
    logger.info("Done to libvirtd configuration")
    return 0


def hypervisor_connecting_test(uri, auth_tls, username,
                               password, logger, expected_result):
    """ connect remote server """
    ret = 0
    try:
        if auth_tls == 'none':
            logger.debug("call libvirt.open()")
            conn = libvirt.open(uri)
        elif auth_tls == 'sasl':
            user_data = [username, password]
            auth = [[libvirt.VIR_CRED_AUTHNAME, libvirt.VIR_CRED_PASSPHRASE], domain_common.request_credentials, user_data]
            logger.debug("call libvirt.openAuth()")
            conn = libvirt.openAuth(uri, auth, 0)
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        ret = 1

    conn.close()

    if ret == 0 and expected_result == 'success':
        logger.info("tls authentication success")
        return 0
    elif ret == 1 and expected_result == 'fail':
        logger.info("tls authentication failed, but that is expected")
        return 0
    elif ret == 0 and expected_result == 'fail':
        logger.error("tls authentication success, but we hope the reverse")
        return 1
    elif ret == 1 and expected_result == 'success':
        logger.error("tls authentication failed")
        return 1

    return 0


def tls_setup_new(params):
    """ Generate tls certificates and configure libvirt """
    logger = params['logger']
    target_machine = params['target_machine']
    username = params['username']
    password = params['password']
    listen_tls = params['listen_tls']
    auth_tls = params['auth_tls']

    uri = "qemu+ssh://%s/system" % target_machine

    local_machine = utils.get_local_hostname()
    target_hostname = utils.get_target_hostname(target_machine, username, password, logger)

    logger.info("Target host: %s" % target_machine)
    logger.info("Local host: %s" % local_machine)
    logger.info("listen_tls: %s" % listen_tls)
    logger.info("auth_tls: %s" % auth_tls)

    if utils.version_compare('libvirt-python', 5, 6, 0, logger):
        logger.info("Because of bug 1741403, change 'listen_tls' to disable.")
        listen_tls = "disable"

    if not utils.do_ping(target_machine, 0):
        logger.error("Failed to ping target host %s" % target_machine)
        return 1

    if os.path.exists(TEMP_TLS_FOLDER):
        shutil.rmtree(TEMP_TLS_FOLDER)
    os.mkdir(TEMP_TLS_FOLDER)

    domain_common.config_ssh(target_machine, username, password, logger)

    if CA_setting_up(target_hostname, logger):
        return 1

    if tls_server_cert(target_hostname, logger):
        return 1

    if tls_client_cert(local_machine, logger):
        return 1

    if deliver_cert(target_machine, username, password, logger):
        return 1

    if auth_tls == 'sasl':
        if sasl_user_add(target_machine, username, password, logger):
            return 1

    if remote_common.set_firewall('16514/tcp', target_machine, username,
                                  password, logger):
        return 1

    if tls_libvirtd_set(target_machine, username, password,
                        listen_tls, auth_tls, logger):
        return 1

    if listen_tls == 'disable':
        if utils.version_compare('libvirt-python', 5, 6, 0, logger):
            if hypervisor_connecting_test(uri, auth_tls, username,
                                          password, logger, 'success'):
                return 1
        else:
            if hypervisor_connecting_test(uri, auth_tls, username,
                                          password, logger, 'fail'):
                return 1
    elif listen_tls == 'enable':
        if hypervisor_connecting_test(uri, auth_tls, username,
                                      password, logger, 'success'):
            return 1

    return 0


def tls_setup_new_clean(params):
    """ cleanup testing enviroment """
    if os.path.exists(TEMP_TLS_FOLDER):
        shutil.rmtree(TEMP_TLS_FOLDER)

    logger = params['logger']
    target_machine = params['target_machine']
    username = params['username']
    password = params['password']
    listen_tls = params['listen_tls']
    auth_tls = params['auth_tls']

    cmd = "rm -f %s/*" % CA_FOLDER
    ret, output = utils.remote_exec_pexpect(target_machine, username,
                                            password, cmd)
    if ret:
        logger.error("Failed to remove ca folder on remote machine")

    shutil.rmtree(CA_FOLDER)

    if auth_tls == 'sasl':
        cmd = "%s -a libvirt -d %s" % (SASLPASSWD2, username)
        ret, output = utils.remote_exec_pexpect(target_machine, username,
                                                password, cmd)
        if ret:
            logger.error("Failed to delete sasl user")

    cmd = "sed -i -n \"/^[ #]/p\" %s" % LIBVIRTD_CONF
    ret, output = utils.remote_exec_pexpect(target_machine, username,
                                            password, cmd)
    if ret:
        logger.error("Failed to restore %s" % LIBVIRTD_CONF)

    cmd = "sed -i -n \"/^[ #]/p\" %s" % SYSCONFIG_LIBVIRTD
    ret, output = utils.remote_exec_pexpect(target_machine, username,
                                            password, cmd)
    if ret:
        logger.error("Failed to restore %s" % SYSCONFIG_LIBVIRTD)

    # Restart remote libvirtd
    remote_common.restart_remote_libvirtd(target_machine, username,
                                          password, logger, 'tls')
