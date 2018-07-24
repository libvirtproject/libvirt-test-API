from utils import utils, nfs

#nfs_path = "/tmp/nfs"
#mount_path = "/var/lib/libvirt/migrate"

required_params = ('target_machine', 'username', 'password', 'nfs_path', 'mount_path')
optional_params = {}

def nfs_env(params):
    """ migrate a guest back and forth between two machines"""
    logger = params['logger']
    target_machine = params['target_machine']
    username = params['username']
    password = params['password']
    nfs_path = params['nfs_path']
    mount_path = params['mount_path']

    server_ip = utils.get_local_hostname()
    if not nfs.nfs_setup(server_ip, target_machine, username, password,
                         nfs_path, mount_path, logger):
        return 1
    return 0


def nfs_env_clean(params):
    logger = params['logger']
    target_machine = params['target_machine']
    username = params['username']
    password = params['password']
    nfs_path = params['nfs_path']
    mount_path = params['mount_path']

    if not nfs.nfs_clean(target_machine, username, password, nfs_path, mount_path, logger):
        logger.error("nfs clean failed.")
