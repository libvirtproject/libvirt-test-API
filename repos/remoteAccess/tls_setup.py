#!/usr/bin/env python

import os
import re
import sys
import pexpect
import string
import shutil
import time

import libvirt
from libvirt import libvirtError

from utils import utils

required_params = ('listen_tls',
                   'auth_tls',
                   'target_machine',
                   'username',
                   'password',)
optional_params = {}

CERTTOOL = "/usr/bin/certtool"
CP = "/bin/cp"
MKDIR = "/bin/mkdir"
CA_FOLDER = "/etc/pki/CA"
SASLPASSWD2 = "/usr/sbin/saslpasswd2"
PRIVATE_KEY_FOLDER = "/etc/pki/libvirt/private"
CERTIFICATE_FOLDER = "/etc/pki/libvirt"
LIBVIRTD_CONF = "/etc/libvirt/libvirtd.conf"
SYSCONFIG_LIBVIRTD = "/etc/sysconfig/libvirtd"

TEMP_TLS_FOLDER = "/tmp/libvirt_test_API_tls"
CAKEY = os.path.join(TEMP_TLS_FOLDER, 'cakey.pem')
CACERT = os.path.join(TEMP_TLS_FOLDER, 'cacert.pem')
SERVERKEY = os.path.join(TEMP_TLS_FOLDER, 'serverkey.pem')
SERVERCERT = os.path.join(TEMP_TLS_FOLDER, 'servercert.pem')
CLIENTKEY = os.path.join(TEMP_TLS_FOLDER, 'clientkey.pem')
CLIENTCERT = os.path.join(TEMP_TLS_FOLDER, 'clientcert.pem')


def CA_setting_up(logger):
    """ setting up a Certificate Authority """
    # Create a private key for CA
    logger.info("generate CA certificates")

    cakey_fd = open(CAKEY, 'w')
    ret, out = utils.exec_cmd(
        [CERTTOOL, '--generate-privkey'], outfile=cakey_fd)
    cakey_fd.close()
    if ret != 0:
        logger.error("failed to create CA private key")
        return 1

    # ca.info file
    cainfo = os.path.join(TEMP_TLS_FOLDER, 'ca.info')
    cainfo_fd = open(cainfo, 'w')
    cainfo_str = ("cn = Libvirt_test_API\n"
                  "ca\n"
                  "cert_signing_key\n")

    cainfo_fd.write(cainfo_str)
    cainfo_fd.close()

    # Generate cacert.pem
    cacert_args = [
        CERTTOOL,
        '--generate-self-signed',
        '--load-privkey',
        CAKEY,
        '--template',
        cainfo]
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
    ret, out = utils.exec_cmd(
        [CERTTOOL, '--generate-privkey'], outfile=serverkey_fd)
    serverkey_fd.close()
    if ret != 0:
        logger.error("failed to create server key")
        return 1

    # server.info
    serverinfo = os.path.join(TEMP_TLS_FOLDER, 'server.info')
    serverinfo_fd = open(serverinfo, 'w')
    serverinfo_str = ("organization = Libvirt_test_API\n"
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
    ret, out = utils.exec_cmd(
        [CERTTOOL, '--generate-privkey'], outfile=clientkey_fd)
    clientkey_fd.close()
    if ret != 0:
        logger.error("failed to create client key")
        return 1

    # client.info
    clientinfo = os.path.join(TEMP_TLS_FOLDER, 'client.info')
    clientinfo_fd = open(clientinfo, 'w')
    clientinfo_str = ("country = xxx\n"
                      "state = xxx\n"
                      "locality = xxx\n"
                      "organization = Libvirt_test_API\n"
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


def deliver_cert(target_machine, username, password, pkipath, logger):
    """ deliver CA, server and client certificates """
    # transmit cacert.pem to remote host
    logger.info(
        "deliver CA, server and client certificates to both local and remote server")
    ret = utils.scp_file(target_machine, username, password, CA_FOLDER, CACERT)
    if ret:
        logger.error("scp cacert.pem to %s error" % target_machine)
        return 1

    # copy cacert.pem to local CA folder
    cacert_cp = [CP, '-f', CACERT, (pkipath and pkipath) or CA_FOLDER]
    ret, out = utils.exec_cmd(cacert_cp)
    if ret:
        logger.error("copying cacert.pem to %s error" % CA_FOLDER)
        return 1

    # mkdir /etc/pki/libvirt/private on remote host
    libvirt_priv_cmd = "mkdir -p %s" % PRIVATE_KEY_FOLDER
    ret, output = utils.remote_exec_pexpect(
        target_machine, username, password, libvirt_priv_cmd)
    if ret:
        logger.error(
            "failed to make /etc/pki/libvirt/private on %s" %
            target_machine)
        return 1

    # transmit serverkey.pem to remote host
    ret = utils.scp_file(
        target_machine,
        username,
        password,
        PRIVATE_KEY_FOLDER,
        SERVERKEY)
    if ret:
        logger.error("failed to scp serverkey.pem to %s" % target_machine)
        return 1

    # transmit servercert.pem to remote host
    ret = utils.scp_file(
        target_machine,
        username,
        password,
        CERTIFICATE_FOLDER,
        SERVERCERT)
    if ret:
        logger.error("failed to scp servercert.pem to %s" % target_machine)
        return 1

    libvirt_priv_cmd_local = [MKDIR, '-p', PRIVATE_KEY_FOLDER]
    ret, out = utils.exec_cmd(libvirt_priv_cmd_local)
    if ret:
        logger.error("failed to make %s on local" % PRIVATE_KEY_FOLDER)
        return 1

    # copy clientkey.pem to local folder
    clientkey_cp = [CP, '-f', CLIENTKEY,
                    (pkipath and pkipath) or PRIVATE_KEY_FOLDER]
    ret, out = utils.exec_cmd(clientkey_cp)
    if ret:
        logger.error("failed to copy clientkey.pem to %s" % PRIVATE_KEY_FOLDER)
        return 1

    # copy clientcert.pem to local folder
    clientcert_cp = [CP, '-f', CLIENTCERT,
                     (pkipath and pkipath) or CERTIFICATE_FOLDER]
    ret, out = utils.exec_cmd(clientcert_cp)
    if ret:
        logger.error(
            "failed to copy clientcert.pem to %s" %
            CERTIFICATE_FOLDER)
        return 1

    logger.info("done to delivery")
    return 0


def sasl_user_add(target_machine, username, password, logger):
    """ execute saslpasswd2 to add sasl user """
    logger.info("add sasl user on server side")
    saslpasswd2_add = "echo %s | %s -a libvirt %s" % (
        password, SASLPASSWD2, username)
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
    # open libvirtd --listen option
    listen_open_cmd = 'echo "LIBVIRTD_ARGS=\\\"--listen\\\"" >> %s' % SYSCONFIG_LIBVIRTD
    ret, output = utils.remote_exec_pexpect(target_machine, username,
                                            password, listen_open_cmd)
    if ret:
        logger.error("failed to uncomment --listen in %s" % SYSCONFIG_LIBVIRTD)
        return 1

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


def request_credentials(credentials, user_data):
    for credential in credentials:
        if credential[0] == libvirt.VIR_CRED_AUTHNAME:
            credential[4] = user_data[0]

            if len(credential[4]) == 0:
                credential[4] = credential[3]
        elif credential[0] == libvirt.VIR_CRED_PASSPHRASE:
            credential[4] = user_data[1]
        else:
            return -1

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


def tls_setup(params):
    """ generate tls certificates and configure libvirt """
    logger = params['logger']
    target_machine = params['target_machine']
    username = params['username']
    password = params['password']
    listen_tls = params['listen_tls']
    auth_tls = params['auth_tls']

    pkipath = ""
    if "pkipath" in params:
        pkipath = params['pkipath']
        if os.path.exists(pkipath):
            shutil.rmtree(pkipath)

        os.mkdir(pkipath)

    uri = "qemu://%s/system" % target_machine
    if pkipath:
        uri += "?pkipath=%s" % pkipath

    local_machine = utils.get_local_hostname()

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

    if iptables_stop(target_machine, username, password, logger):
        return 1

    if CA_setting_up(logger):
        return 1

    if tls_server_cert(target_machine, logger):
        return 1

    if tls_client_cert(local_machine, logger):
        return 1

    if deliver_cert(target_machine, username,
                    password, pkipath, logger):
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


def tls_setup_clean(params):
    """ cleanup testing enviroment """
    if os.path.exists(TEMP_TLS_FOLDER):
        shutil.rmtree(TEMP_TLS_FOLDER)

    logger = params['logger']
    target_machine = params['target_machine']
    username = params['username']
    password = params['password']
    listen_tls = params['listen_tls']
    auth_tls = params['auth_tls']

    cacert_rm = "rm -f %s/cacert.pem" % CA_FOLDER
    ret, output = utils.remote_exec_pexpect(target_machine, username,
                                            password, cacert_rm)
    if ret:
        logger.error("failed to remove cacert.pem on remote machine")

    ca_libvirt_rm = "rm -rf %s" % CERTIFICATE_FOLDER
    ret, output = utils.remote_exec_pexpect(target_machine, username,
                                            password, ca_libvirt_rm)
    if ret:
        logger.error("failed to remove libvirt folder")

    os.remove("%s/cacert.pem" % CA_FOLDER)
    shutil.rmtree(CERTIFICATE_FOLDER)

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
