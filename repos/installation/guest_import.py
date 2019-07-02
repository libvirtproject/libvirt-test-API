import os
import time
import shutil
import libvirt

from libvirt import libvirtError
from utils import utils

required_params = ('guestname',)
optional_params = {
                   'memory': 2097152,
                   'vcpu': 2,
                   'imagepath': '/var/lib/libvirt/images/libvirt-ci.qcow2',
                   'diskpath': '/var/lib/libvirt/images/libvirt-test-api',
                   'imageformat': 'qcow2',
                   'hddriver': 'virtio',
                   'nicdriver': 'virtio',
                   'macaddr': '52:54:00:97:e4:28',
                   'uuid': '05867c1a-afeb-300e-e55e-2673391ae080',
                   'type': 'define',
                   'xml': 'xmls/guest_import.xml',
                   'guestmachine': 'pc',
                   'networksource': 'default',
                   'video': 'qxl',
                   'graphic': 'spice',
                   'guestarch': 'x86_64'}


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


def guest_import(params):
    """ Using an exist image to import a guest """
    logger = params['logger']
    guestname = params.get('guestname')
    xmlstr = params.get('xml')
    guestarch = params.get('guestarch', 'x86_64')
    guestmachine = params.get('guestmachine', 'pc')
    video = params.get('video', 'qxl')
    graphic = params.get('graphic', 'spice')
    hddriver = params.get('hddriver', 'virtio')
    installtype = params.get('type', 'define')
    imageformat = params.get('imageformat', 'qcow2')
    diskpath = params.get('diskpath', '/var/lib/libvirt/images/libvirt-test-api')
    imagepath = params.get('imagepath', '/var/lib/libvirt/images/libvirt-ci.qcow2')

    logger.info("guest name: %s" % guestname)
    logger.info("image path: %s" % imagepath)
    logger.info("disk path: %s" % diskpath)

    if os.path.exists(diskpath):
        os.remove(diskpath)
    backup_img_format = utils.get_image_format(imagepath, logger)
    if imageformat == "raw" and backup_img_format == "qcow2":
        new_backup_img = imagepath + '.raw'
        cmd = "qemu-img convert %s %s" % (imagepath, new_backup_img)
        ret, out = utils.exec_cmd(cmd, shell=True)
        if ret:
            logger.error("convert img from qcow2 to raw failed.")
            return 1
        shutil.copyfile(new_backup_img, diskpath)
    else:
        shutil.copyfile(imagepath, diskpath)
    os.chown(diskpath, 107, 107)

    if hddriver == 'virtio':
        xmlstr = xmlstr.replace('DEV', 'vda')
    elif hddriver == 'ide':
        xmlstr = xmlstr.replace('DEV', 'hda')
    elif hddriver == 'scsi':
        xmlstr = xmlstr.replace('DEV', 'sda')

    logger.info('dump guest xml:\n%s' % xmlstr)

    try:
        conn = libvirt.open()
        check_domain_state(conn, guestname, logger)

        if installtype == 'define':
            logger.info('define guest:')
            domobj = conn.defineXML(xmlstr)
            time.sleep(3)
            domobj.create()
        elif installtype == 'create':
            logger.info('create guest:')
            domobj = conn.createXML(xmlstr, 0)
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    logger.info("guest is booting up")
    time.sleep(20)
    mac = utils.get_dom_mac_addr(guestname)
    logger.info("mac address: %s" % mac)
    ip = utils.mac_to_ip(mac, 150)
    if not ip:
        logger.error("guest %s start failed." % guestname)
        return 1
    else:
        logger.info("guest ip: %s" % ip)
        logger.info("guest %s start successfully." % guestname)

    return 0


def guest_import_clean(params):
    """ clean a guest """
    logger = params['logger']
    guestname = params.get('guestname')
    diskpath = params.get('diskpath', '/var/lib/libvirt/images/libvirt-test-api')

    try:
        conn = libvirt.open()
        check_domain_state(conn, guestname, logger)
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))

    if os.path.exists(diskpath):
        os.remove(diskpath)
