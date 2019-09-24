from utils import process
from utils import utils
from utils import nfs

#nfs_path = "/tmp/nfs"
#mount_path = "/var/lib/libvirt/migrate"

required_params = ('nfs_path', 'mount_path')
optional_params = {'target_machine': None,
                   'username': 'root',
                   'password': 'redhat'}


def nfs_env(params):
    """ migrate a guest back and forth between two machines"""
    logger = params['logger']
    target_machine = params.get('target_machine', None)
    username = params.get('username', 'root')
    password = params.get('password', 'redhat')
    nfs_path = params['nfs_path']
    mount_path = params['mount_path']

    server_ip = utils.get_local_ip()
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
