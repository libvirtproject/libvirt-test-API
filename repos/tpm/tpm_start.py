import os
import time
import shutil
import libvirt

from libvirt import libvirtError
from utils import utils
from utils import process

required_params = ('guestname',)
optional_params = {
                   'imagepath': '/var/lib/libvirt/images/libvirt-ci.qcow2',
                   'diskpath': '/var/lib/libvirt/images/libvirt-test-api',
                   'xml': 'xmls/tpm.xml',
                   'guestmachine': 'pc',
                   'video': 'qxl',
                   'graphic': 'spice',
                   'guestarch': 'x86_64',
                   'negative': None}


def check_domain_state(conn, guestname, logger):
    """ if a guest with the same name exists, remove it """
    running_guests = []
    ids = conn.listDomainsID()
    for id in ids:
        obj = conn.lookupByID(id)
        running_guests.append(obj.name())

    if guestname in running_guests:
        logger.info("A guest with the same name %s is running!" % guestname)
        logger.info("destroy it...")
        domobj = conn.lookupByName(guestname)
        domobj.destroy()

    defined_guests = conn.listDefinedDomains()

    if guestname in defined_guests:
        logger.info("undefine the guest with the same name %s" % guestname)
        domobj = conn.lookupByName(guestname)
        domobj.undefineFlags(libvirt.VIR_DOMAIN_UNDEFINE_MANAGED_SAVE)
    time.sleep(3)
    return 0


def tpm_start(params):
    """ Start a guest with TPM """
    logger = params['logger']
    guestname = params.get('guestname')
    xmlstr = params.get('xml')
    guestarch = params.get('guestarch', 'x86_64')
    guestmachine = params.get('guestmachine', 'pc')
    video = params.get('video', 'qxl')
    graphic = params.get('graphic', 'spice')
    diskpath = params.get('diskpath', '/var/lib/libvirt/images/libvirt-test-api')
    imagepath = params.get('imagepath', '/var/lib/libvirt/images/libvirt-ci.qcow2')
    negative = params.get('negative', None)

    logger.info("guest name: %s" % guestname)
    logger.info("image path: %s" % imagepath)
    logger.info("disk path: %s" % diskpath)

    if not utils.version_compare('libvirt-python', 5, 6, 0, logger):
        logger.info("Current libvirt-python don't support VIR_FROM_TPM.")
        return 0

    if negative is not None and negative == "tpm":
        cmd = "rpm -q swtpm-tools"
        ret = process.system(cmd, shell=True, ignore_status=True)
        if not ret:
            logger.info("Package swtpm-tools exist, remove it.")
            cmd = "rpm -e swtpm-tools"
            if process.system(cmd, shell=True, ignore_status=True):
                logger.error("Remove package swtpm failed.")
                return 1

    diskdir = os.path.dirname(diskpath)
    if not os.path.exists(diskdir):
        os.mkdir(diskdir)
    if os.path.exists(diskpath):
        os.remove(diskpath)
    shutil.copyfile(imagepath, diskpath)
    os.chown(diskpath, 107, 107)

    logger.info('dump guest xml:\n%s' % xmlstr)

    try:
        conn = libvirt.open()
        check_domain_state(conn, guestname, logger)
        logger.info('create guest:')
        domobj = conn.createXML(xmlstr, 0)
    except libvirtError as err:
        logger.error("API error message: %s, error domain: %s"
                     % (err.get_error_message(), err.get_error_domain()))
        if negative is not None and negative == "tpm":
            if err.get_error_domain() == 70:
                logger.info("PASS: negative test VIR_FROM_TPM succeed.")
            else:
                logger.info("FAIL: negative test VIR_FROM_TPM failed.")
                return 1
    return 0


def tpm_start_clean(params):
    """ clean a guest """
    logger = params['logger']
    guestname = params.get('guestname')
    diskpath = params.get('diskpath', '/var/lib/libvirt/images/libvirt-test-api')

    try:
        conn = libvirt.open()
        check_domain_state(conn, guestname, logger)
    except libvirtError as err:
        logger.error("API error message: %s, error code is %s"
                     % (err.get_error_message(), err.get_error_code()))

    if os.path.exists(diskpath):
        os.remove(diskpath)
