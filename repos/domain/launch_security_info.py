import libvirt

from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('guestname',)
optional_params = {}


def launch_security_info(params):
    guestname = params['guestname']
    logger = params['logger']

    if not utils.version_compare("libvirt-python", 4, 5, 0, logger):
        logger.info("Current libvirt-python don't support launchSecurityInfo().")
        return 0

    conn = sharedmod.libvirtobj['conn']
    dom = conn.lookupByName(guestname)

    try:
        info = dom.launchSecurityInfo(0)
        logger.info("get launch security info: %s" % info)
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1
    logger.info('PASS')
    return 0
