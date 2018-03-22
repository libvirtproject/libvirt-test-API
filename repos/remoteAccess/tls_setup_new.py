#!/usr/bin/env python

import os
import shutil
import time

import libvirt
from libvirt import libvirtError

from utils import utils, process
from repos.domain.domain_common import ssh_keygen, ssh_tunnel, request_credentials

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
    logger.info("setting libvirtd.conf on tls server")

    # set listen_tcp
    logger.info("set listen_tcp to 0 in %s" % LIBVIRTD_CONF)
    listen_tcp_disable = "echo \"listen_tcp = 0\" >> %s" % LIBVIRTD_CONF
    ret, output = utils.remote_exec_pexpect(target_machine, username,
                                            password, listen_tcp_disable)
    if ret:
        logger.error("failed to set listen_tcp to 0 in %s" % LIBVIRTD_CONF)
        return 1

    # set listen_tls
    if listen_tls == 'enable':
        logger.info("set listen_tls to 1 in %s" % LIBVIRTD_CONF)
        listen_tls_enable = "echo \"listen_tls = 1\" >> %s" % LIBVIRTD_CONF
        ret, output = utils.remote_exec_pexpect(target_machine, username,
                                                password, listen_tls_enable)
        if ret:
            logger.error("failed to set listen_tls to 1 in %s" % LIBVIRTD_CONF)
            return 1
    elif listen_tls == 'disable':
        logger.info("set listen_tls = 0 in %s" % LIBVIRTD_CONF)
        listen_tls_set = "echo 'listen_tls = 0' >> %s" % LIBVIRTD_CONF
        ret, output = utils.remote_exec_pexpect(target_machine, username,
                                                password, listen_tls_set)
        if ret:
            logger.error("failed to set listen_tls in %s" % LIBVIRTD_CONF)
            return 1

    # set auth_tls
    logger.info("set auth_tls = %s in %s" % (auth_tls, LIBVIRTD_CONF))
    auth_tls_set = 'echo "auth_tls = \\\"%s\\\"" >> %s' % (auth_tls, LIBVIRTD_CONF)
    ret, output = utils.remote_exec_pexpect(target_machine, username,
                                            password, auth_tls_set)
    if ret:
        logger.error("failed to set auth_tls in %s" % LIBVIRTD_CONF)
        return 1

    # restart remote libvirtd service
    libvirtd_restart_cmd = "service libvirtd restart"
    logger.info("libvirtd restart")
    ret, output = utils.remote_exec_pexpect(target_machine, username,
                                            password, libvirtd_restart_cmd)
    if ret:
        logger.error("failed to restart libvirtd service")
        return 1

    time.sleep(3)
    logger.info("done to libvirtd configuration")
    return 0


def iptables_stop(target_machine, username, password, logger):
    """ This is a temprory method in favor of migration """
    logger.info("check local and remote iptables status")

    check_cmd = "systemctl status iptables"
    logger.debug("cmd : %s" % check_cmd)
    ret, out = utils.remote_exec_pexpect(target_machine, username,
                                         password, check_cmd)
    logger.debug("ret = %s, out = %s" % (ret, out))
    if ret == 0:
        logger.info("stop remote iptables temprorily")
        stop_cmd = "systemctl stop iptables"
        ret, output = utils.remote_exec_pexpect(target_machine, username,
                                                password, stop_cmd)
        if ret:
            logger.error("failed to stop remote iptables service, %s" % ret)
            logger.error("output: %s" % output)
            return 1

    ret, out = utils.exec_cmd(check_cmd, shell=True)
    logger.debug("ret = %s, out = %s" % (ret, out))
    if ret == 0:
        logger.info("stop local iptables temprorily")
        stop_cmd = "systemctl stop iptables"
        ret, output = utils.exec_cmd(stop_cmd, shell=True)
        if ret:
            logger.error("failed to stop local iptables service, %s" % ret)
            logger.error("output: %s" % output)
            return 1

    logger.info("done the iptables stop job")
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
            auth = [[libvirt.VIR_CRED_AUTHNAME, libvirt.VIR_CRED_PASSPHRASE], request_credentials, user_data]
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
    """ generate tls certificates and configure libvirt """
    logger = params['logger']
    target_machine = params['target_machine']
    username = params['username']
    password = params['password']
    listen_tls = params['listen_tls']
    auth_tls = params['auth_tls']

    uri = "qemu+ssh://%s/system" % target_machine

    local_machine = utils.get_local_hostname()
    target_hostname = utils.get_target_hostname(target_machine, username, password, logger)

    logger.info("the hostname of server is %s" % target_machine)
    logger.info("the hostname of local machine is %s" % local_machine)
    logger.info("the value of listen_tls is %s" % listen_tls)
    logger.info("the value of auth_tls is %s" % auth_tls)

    if not utils.do_ping(target_machine, 0):
        logger.error("failed to ping host %s" % target_machine)
        return 1

    if os.path.exists(TEMP_TLS_FOLDER):
        shutil.rmtree(TEMP_TLS_FOLDER)

    os.mkdir(TEMP_TLS_FOLDER)

    ret = ssh_keygen(logger)
    if ret:
        logger.error("failed to generate RSA key")
        return 1
    ret = ssh_tunnel(target_machine, username, password, logger)
    if ret:
        logger.error("failed to setup ssh tunnel with target machine %s" % target_machine)
        return 1

    process.run("ssh-add", shell=True, ignore_status=True)

    if iptables_stop(target_machine, username, password, logger):
        return 1

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

    if tls_libvirtd_set(target_machine, username, password,
                        listen_tls, auth_tls, logger):
        return 1

    if listen_tls == 'disable':
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

    cafolder_rm = "rm -f %s/*" % CA_FOLDER
    ret, output = utils.remote_exec_pexpect(target_machine, username,
                                            password, cafolder_rm)
    if ret:
        logger.error("failed to remove ca folder on remote machine")

    shutil.rmtree(CA_FOLDER)

    if auth_tls == 'sasl':
        saslpasswd2_delete = "%s -a libvirt -d %s" % (SASLPASSWD2, username)
        ret, output = utils.remote_exec_pexpect(target_machine, username,
                                                password, saslpasswd2_delete)
        if ret:
            logger.error("failed to delete sasl user")

    libvirtd_conf_retore = "sed -i -n \"/^[ #]/p\" %s" % LIBVIRTD_CONF
    ret, output = utils.remote_exec_pexpect(target_machine, username,
                                            password, libvirtd_conf_retore)
    if ret:
        logger.error("failed to restore %s" % LIBVIRTD_CONF)

    sysconfig_libvirtd_restore = "sed -i -n \"/^[ #]/p\" %s" % SYSCONFIG_LIBVIRTD
    ret, output = utils.remote_exec_pexpect(target_machine, username,
                                            password, sysconfig_libvirtd_restore)
    if ret:
        logger.error("failed to restore %s" % SYSCONFIG_LIBVIRTD)

    # restart remote libvirtd service
    libvirtd_restart_cmd = "service libvirtd restart"
    logger.info("libvirtd restart")
    ret, output = utils.remote_exec_pexpect(target_machine, username,
                                            password, libvirtd_restart_cmd)
    if ret:
        logger.error("failed to restart libvirtd service")
