from utils import process
from utils import utils
from utils import nfs

#nfs_path = "/tmp/nfs"
#mount_path = "/var/lib/libvirt/migrate"

required_params = ('nfs_path', 'mount_path')
optional_params = {'target_machine': None,
                   'username': 'root',
                   'password': 'redhat'}


def stop_firewalld(target_machine, logger):
    """ Stop firewalld service (not recommended, """
    """ this will affect virtual network of libvirtd.) """
    cmd = "systemctl stop firewalld"
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("Stop firewalld service failed: %s." % ret.stdout)
        return 1
    if target_machine is not None:
        cmd = "systemctl stop firewalld"
        ret, out = utils.remote_exec_pexpect(target_machine, username, password, cmd, 120)
        if ret:
            logger.error("Stop remote firewalld failed: %s" % out)
            return 1


def nfs_env(params):
    """ migrate a guest back and forth between two machines"""
    logger = params['logger']
    target_machine = params.get('target_machine', None)
    username = params.get('username', 'root')
    password = params.get('password', 'redhat')
    nfs_path = params['nfs_path']
    mount_path = params['mount_path']

    server_ip = utils.get_local_ip()
    cmd = ("firewall-cmd --add-port=49152-49215/tcp;"
           "firewall-cmd --permanent --add-service=nfs;"
           "firewall-cmd --permanent --add-service=mountd;"
           "firewall-cmd --permanent --add-service=rpc-bind;"
           "firewall-cmd --reload")
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("Failed to add nfs service to firewalld: %s." % ret.stdout)
        return 1
    if target_machine is not None:
        ret, out = utils.remote_exec_pexpect(target_machine, username, password, cmd, 120)
        if ret:
            logger.error("Failed to add nfs service to remote firewalld: %s" % out)
            return 1
    if not nfs.nfs_setup(server_ip, target_machine, username, password,
                         nfs_path, mount_path, logger):
        return 1
    return 0


def nfs_env_clean(params):
    logger = params['logger']
    target_machine = params.get('target_machine', None)
    username = params.get('username', 'root')
    password = params.get('password', 'redhat')
    nfs_path = params['nfs_path']
    mount_path = params['mount_path']

    if not nfs.nfs_clean(target_machine, username, password, nfs_path, mount_path, logger):
        logger.error("nfs clean failed.")
