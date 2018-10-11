import os
import re
import time
import shutil
import libvirt

from libvirt import libvirtError
from src import env_parser
from utils import utils

required_params = ('guestname',)
optional_params = {
    'memory': 2048576,
    'vcpu': 1,
    'imagepath': '/var/lib/libvirt/images/libvirt-ci.qcow2',
    'diskpath': '/var/lib/libvirt/images/libvirt-test-api',
    'imageformat': 'qcow2',
                   'hddriver': 'virtio',
                   'nicdriver': 'virtio',
                   'macaddr': '52:54:00:97:e4:28',
                   'uuid': '05867c1a-afeb-300e-e55e-2673391ae080',
                   'type': 'define',
                   'xml': 'xmls/kvm_linux_guest_install_import.xml',
                   'guestmachine': 'pc',
                   'networksource': 'default',
                   'bridgename': 'virbr0',
                   'video': 'qxl',
                   'graphic': 'spice',
                   'guestarch': 'x86_64'
}

HOME_PATH = os.getcwd()


def prepare_boot_guest(domobj, xmlstr, guestname, installtype, diskpath, logger):
    """ After guest installation is over, undefine the guest with
        bootting off cdrom, to define the guest to boot off harddisk.
    """
    xmlstr = xmlstr.replace('<boot dev="cdrom"/>', '<boot dev="hd"/>')
    xmlstr = re.sub('<disk device="cdrom".*\n.*\n.*\n.*\n.*\n', '', xmlstr)

    if installtype != 'create':
        domobj.undefine()
        logger.info("undefine %s : \n" % guestname)

    try:
        conn = domobj._conn
        domobj = conn.defineXML(xmlstr)
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("fail to define domain %s" % guestname)
        return 1

    logger.info("define guest %s " % guestname)
    logger.debug("the xml description of guest booting off harddisk is %s" %
                 xmlstr)

    logger.info('boot guest up ...')
    time.sleep(5)
    # Add for test following error:
    #   internal error: process exited while connecting to monitor: 2018-10-09T05:34:38.865865Z
    #   qemu-kvm: -drive file=/tmp/snapshot_netfs/libvirt-test-api,format=qcow2,if=none,id=drive-virtio-disk0:
    #   Failed to get "write" lock
    #   Is another process using the image?, error code is 1
    if diskpath == "/var/lib/libvirt/snapshot_nfs/libvirt-test-api":
        cmd = "lsof | grep %s" % diskpath
        ret, out = utils.exec_cmd(cmd, shell=True)
        if ret:
            logger.error("cmd: %s" % cmd)
            logger.error("out: %s" % out)
        cmd = "lslocks | grep %s" % diskpath
        ret, out = utils.exec_cmd(cmd, shell=True)
        if ret:
            logger.error("cmd: %s" % cmd)
            logger.error("out: %s" % out)
    #End test

    try:
        domobj.create()
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("fail to start domain %s" % guestname)
        return 1

    return 0


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
        domobj.undefine()

    return 0


def install_linux_import(params):
    """ install a new virtual machine """
    logger = params['logger']

    guestname = params.get('guestname')
    br = params.get('bridgename', 'virbr0')
    xmlstr = params['xml']

    logger.info("the name of guest is %s" % guestname)

    if utils.isPower():
        guestmachine = "persies"
        xmlstr = xmlstr.replace('GUESTMACHINE', guestmachine)
        video = params.get('video', 'vga')
        xmlstr = xmlstr.replace('VIDEO', video)
        graphic = params.get('graphic', 'vnc')
        xmlstr = xmlstr.replace('GRAPHIC', graphic)
    else:
        video = params.get('video', 'qxl')
        xmlstr = xmlstr.replace('VIDEO', video)
        graphic = params.get('graphic', 'spice')
        xmlstr = xmlstr.replace('GRAPHIC', graphic)

    conn = libvirt.open()
    check_domain_state(conn, guestname, logger)

    logger.info("the macaddress is %s" %
                params.get('macaddr', '52:54:00:97:e4:28'))

    imagepath = params.get('imagepath', '/var/lib/libvirt/images/libvirt-ci.qcow2')
    logger.info("using image %s" % imagepath)
    diskpath = params.get('diskpath', '/var/lib/libvirt/images/libvirt-test-api')
    logger.info("disk image is %s" % diskpath)
    imageformat = params.get('imageformat', 'qcow2')
    xmlstr = xmlstr.replace('IMAGEFORMAT', imageformat)

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

    hddriver = params.get('hddriver', 'virtio')
    if hddriver == 'virtio':
        xmlstr = xmlstr.replace('DEV', 'vda')
    elif hddriver == 'ide':
        xmlstr = xmlstr.replace('DEV', 'hda')
    elif hddriver == 'scsi':
        xmlstr = xmlstr.replace('DEV', 'sda')

    logger.info("get system environment information")
    envfile = os.path.join(HOME_PATH, 'global.cfg')
    logger.info("the environment file is %s" % envfile)

    envparser = env_parser.Envparser(envfile)
    cache_folder = envparser.get_value("variables", "domain_cache_folder")
    logger.info('dump guest xml:\n%s' % xmlstr)

    installtype = params.get('type', 'define')
    if installtype == 'define':
        logger.info('define guest from xml description')
        try:
            domobj = conn.defineXML(xmlstr)
        except libvirtError as e:
            logger.error("API error message: %s, error code is %s"
                         % (e.get_error_message(), e.get_error_code()))
            logger.error("fail to define domain %s" % guestname)
            return 1
        ret = prepare_boot_guest(domobj, xmlstr, guestname, installtype, diskpath, logger)
        if ret:
            logger.info("booting guest vm off harddisk failed")
            return 1
    elif installtype == 'create':
        logger.info('create guest from xml description')
        try:
            domobj = conn.createXML(xmlstr, 0)
        except libvirtError as e:
            logger.error("API error message: %s, error code is %s"
                         % (e.get_error_message(), e.get_error_code()))
            logger.error("fail to define domain %s" % guestname)
            return 1
        guest_names = []
        ids = conn.listDomainsID()
        for id in ids:
            obj = conn.lookupByID(id)
            guest_names.append(obj.name())

        if guestname not in guest_names:
            logger.info("define the vm and boot it up")
            ret = prepare_boot_guest(domobj, xmlstr, guestname, installtype, diskpath, logger)
            if ret:
                logger.info("booting guest vm off harddisk failed")
                return 1

    logger.info("guest is booting up")

    logger.info("get the mac address of vm %s" % guestname)
    mac = utils.get_dom_mac_addr(guestname)
    logger.info("the mac address of vm %s is %s" % (guestname, mac))

    timeout = 300

    while timeout:
        time.sleep(10)
        timeout -= 10

        ip = utils.mac_to_ip(mac, 180, br)

        if not ip:
            logger.info(str(timeout) + "s left")
        else:
            logger.info("vm %s power on successfully" % guestname)
            logger.info("the ip address of vm %s is %s" % (guestname, ip))
            break

    if timeout == 0:
        logger.info("fail to power on vm %s" % guestname)
        return 1

    time.sleep(60)

    return 0
