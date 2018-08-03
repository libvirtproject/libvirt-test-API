#!/usr/bin/env python
import os
import shutil
import re
import requests
import libvirt
import time
import sys

from src import env_parser
from utils import utils
from libvirt import libvirtError
from six.moves import urllib

brickpath = "/tmp/test-api-brick"
imagename = "libvirt-test-api"

BOOT_DIR = "/var/lib/libvirt/boot"
VMLINUZ = os.path.join(BOOT_DIR, 'vmlinuz')
INITRD = os.path.join(BOOT_DIR, 'initrd.img')


def setup_storage(params, mountpath, logger):
    storage = params.get('storage', 'local')
    sourcehost = params.get('sourcehost')
    sourcepath = params.get('sourcepath')
    seeksize = params.get('disksize', 20)
    imageformat = params.get('imageformat', 'qcow2')
    diskpath = ""

    if storage == "local":
        diskpath = params.get('diskpath', "/var/lib/libvirt/images/libvirt-test-api")
        remove_all(diskpath, logger)
        create_image(diskpath, seeksize, imageformat, logger)
    else:
        if storage == "gluster":
            if not os.path.isdir(brickpath):
                os.mkdir(brickpath, 0o755)
            utils.setup_gluster("test-api-gluster", utils.get_local_hostname(), brickpath, logger)
            utils.mount_gluster("test-api-gluster", utils.get_local_hostname(), mountpath, logger)
            diskpath = mountpath + "/" + imagename
            remove_all(diskpath, logger)
            create_image(diskpath, seeksize, imageformat, logger)
        elif storage == "nfs":
            utils.setup_nfs(sourcehost, sourcepath, mountpath, logger)
            diskpath = mountpath + "/" + imagename
            remove_all(diskpath, logger)
            create_image(diskpath, seeksize, imageformat, logger)
        elif storage == "iscsi":
            utils.setup_iscsi(sourcehost, sourcepath, mountpath, logger)
        else:
            logger.error("%s is not exists." % storage)
    return diskpath


def cleanup_storage(params, mountpath, logger):
    storage = params.get('storage', 'local')
    sourcepath = params.get('sourcepath')
    if storage == "gluster":
        utils.umount_gluster(mountpath, logger)
        utils.cleanup_gluster("test-api-gluster", logger)
        if os.path.isdir(brickpath):
            shutil.rmtree(brickpath)
    elif storage == "nfs":
        utils.cleanup_nfs(mountpath, logger)
    elif storage == "iscsi":
        utils.cleanup_iscsi(sourcepath, mountpath, logger)
    if os.path.exists(mountpath):
        shutil.rmtree(mountpath)


def get_iscsi_disk_path(portal, target):
    dev_path = "/dev/disk/by-path/"
    if os.path.exists(dev_path):
        disk = "ip-%s:3260-iscsi-%s-lun" % (portal, target)
        devices = []
        devices = os.listdir(dev_path)
        for dev in devices:
            if disk in dev and "-part" not in dev:
                return (dev_path + dev)
    return ""


def get_path_from_url(url, key):
    web_con = requests.get(url)
    match = re.compile(r'<a href=".*">.*%s</a>' % key)
    if sys.version_info[0] < 3:
        name = re.findall(match, web_con.content)[0].split("\"")[1]
    else:
        name = re.findall(match, utils.decode_to_text(web_con.content))[0].split("\"")[1]
    path = "%s/%s" % (url, name)
    return path


def get_iso_link(rhelnewest, guestos, guestarch, logger):
    local_url = get_value_from_global("other", "local_url")
    remote_url = get_value_from_global("other", "remote_url")
    location = utils.get_local_hostname()
    isolink = ""
    if rhelnewest is not None:
        if local_url in rhelnewest:
            repo_name = rhelnewest.split('/')[6]
        elif remote_url in rhelnewest:
            repo_name = rhelnewest.split('/')[4]
        isolink = ("%s%s/iso/%s-Server-%s-dvd1.iso" %
                   (rhelnewest, guestarch, repo_name, guestarch))
    else:
        os_arch = guestos + "_" + guestarch
        if "pek2" in location:
            isolink = local_url + get_value_from_global("guest", os_arch + "_iso")
        else:
            isolink = remote_url + get_value_from_global("guest", os_arch + "_iso")
    logger.info("ISO link: %s" % isolink)
    return isolink


def get_release_ostree(guestos, guestarch):
    local_url = get_value_from_global("other", "local_url")
    remote_url = get_value_from_global("other", "remote_url")
    location = utils.get_local_hostname()
    os_arch = guestos + "_" + guestarch
    ostree = ""
    if "pek2" in location:
        ostree = local_url + get_value_from_global("guest", os_arch)
    else:
        ostree = remote_url + get_value_from_global("guest", os_arch)
    return ostree


def get_version(rhelnewest):
    tree_list = rhelnewest.split("/")
    for ver in tree_list:
        if "RHEL" in ver and "ALT" in ver:
            return ver.split("-")[2]
        elif "RHEL" in ver:
            return ver.split("-")[1]
    return ""


def get_ostree(rhelnewest, guestos, guestarch, logger):
    ostree = ""
    if rhelnewest is None:
        ostree = get_release_ostree(guestos, guestarch)
    else:
        release_ver = get_value_from_global("other", "release_ver")
        location = utils.get_local_hostname()
        version = get_version(rhelnewest)
        if version in release_ver:
            guestos = "rhel" + version.replace('.', 'u')
            ostree = get_release_ostree(guestos, guestarch)
        else:
            ostree = rhelnewest + "/%s/os" % guestarch
    logger.info("Install source: %s" % ostree)
    return ostree


def get_kscfg(rhelnewest, guestos, guestarch, installmethod, logger):
    os_arch = guestos + "_" + guestarch
    kscfg = ""
    if rhelnewest is None:
        kscfg = get_value_from_global("guest", os_arch + "_%s_ks" % installmethod)
    else:
        release_ver = get_value_from_global("other", "release_ver")
        location = utils.get_local_hostname()
        version = get_version(rhelnewest)
        if version in release_ver:
            guestos = "rhel" + version.replace('.', 'u')
            os_arch = guestos + "_" + guestarch
            kscfg = get_value_from_global("guest", os_arch + "_%s_ks" % installmethod)
        else:
            kscfg = get_value_from_global("guest", "rhel%s_newest_%s_%s_ks" %
                                          (version.split(".")[0], guestarch, installmethod))
    logger.info('Kisckstart file: %s' % kscfg)
    return kscfg


def clean_guest(guestname, logger):
    conn = libvirt.open(None)
    running_guests = []
    ids = conn.listDomainsID()
    for id in ids:
        obj = conn.lookupByID(id)
        running_guests.append(obj.name())

    if guestname in running_guests:
        logger.info("Destroy guest: %s" % guestname)
        domobj = conn.lookupByName(guestname)
        domobj.destroy()

    define_guests = conn.listDefinedDomains()
    if guestname in define_guests:
        logger.info("Undefine guest: %s" % guestname)
        domobj = conn.lookupByName(guestname)
        domobj.undefine()
    conn.close()


def get_value_from_global(section, option):
    pwd = os.getcwd()
    envfile = os.path.join(pwd, 'global.cfg')
    envparser = env_parser.Envparser(envfile)
    return envparser.get_value(section, option)


def remove_all(path, logger):
    logger.debug("Remove %s." % path)
    if os.path.isfile(path):
        os.remove(path)
    elif os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)


def check_guest_ip(guestname, logger, bridge='virbr0'):
    mac = utils.get_dom_mac_addr(guestname)

    logger.info("MAC address: %s" % mac)

    timeout = 300
    while timeout:
        time.sleep(10)
        timeout -= 10
        ip = utils.mac_to_ip(mac, 180, bridge)

        if not ip:
            logger.info(str(timeout) + "s left")
        else:
            logger.info("Guest %s start successfully" % guestname)
            logger.info("IP address: %s" % ip)
            break

    if timeout == 0:
        logger.info("Guest %s start failed." % guestname)
        return False
    return True


def get_boot_driver(hddriver, logger):
    boot_driver = 'vda'
    driver_list = ['scsi', 'stat', 'scsilun']
    if hddriver == 'ide':
        boot_driver = 'hda'
    elif any(driver in hddriver for driver in driver_list):
        boot_driver = 'sda'
    logger.debug("Boot driver: %s" % boot_driver)
    return boot_driver


def set_disk_xml(hddriver, xmlstr, diskpath, logger, sourcehost=None, sourcepath=None):
    if hddriver == 'virtio':
        xmlstr = xmlstr.replace('DEV', 'vda')
    elif hddriver == 'ide':
        xmlstr = xmlstr.replace('DEV', 'hda')
    elif hddriver == 'scsi':
        xmlstr = xmlstr.replace('DEV', 'sda')
    elif hddriver == "sata":
        xmlstr = xmlstr.replace("DEV", 'sda')
    elif hddriver == 'lun':
        xmlstr = xmlstr.replace("'lun'", "'virtio'")
        xmlstr = xmlstr.replace('DEV', 'vda')
        xmlstr = xmlstr.replace('"file"', '"block"')
        xmlstr = xmlstr.replace('"disk"', '"lun"')
        iscsi_path = get_iscsi_disk_path(sourcehost, sourcepath)
        xmlstr = xmlstr.replace("file='%s'" % diskpath, "dev='%s'" % iscsi_path)
        xmlstr = xmlstr.replace('device="cdrom" type="block">', 'device="cdrom" type="file">')
    elif hddriver == 'scsilun':
        xmlstr = xmlstr.replace("'scsilun'", "'scsi'")
        xmlstr = xmlstr.replace('DEV', 'sda')
        xmlstr = xmlstr.replace('"file"', '"block"')
        xmlstr = xmlstr.replace('"disk"', '"lun"')
        iscsi_path = get_iscsi_disk_path(sourcehost, sourcepath)
        xmlstr = xmlstr.replace("file='%s'" % diskpath, "dev='%s'" % iscsi_path)
        xmlstr = xmlstr.replace('device="cdrom" type="block">', 'device="cdrom" type="file">')
    elif hddriver == 'usb':
        xmlstr = xmlstr.replace("DEV", 'sda')

    return xmlstr


def create_image(diskpath, seeksize, imageformat, logger, ver='v3'):
    options = ""
    if ver and imageformat == "qcow2":
        if ver.startswith('v3'):
            options = "-o compat=1.1"
            if ver.endswith('lazy_refcounts'):
                options = options + " -o lazy_refcounts=on"

    cmd = "qemu-img create -f %s %s %s %sG" % (imageformat, options, diskpath, seeksize)
    logger.info("cmd: %s" % cmd)
    ret, out = utils.exec_cmd(cmd, shell=True)
    if ret:
        logger.debug(out)
        logger.info("creating disk image file is fail")
        return False

    os.chown(diskpath, 107, 107)
    return True


def set_video_xml(video, xmlstr):
    if video == "qxl":
        video_model = ("<model type='qxl' ram='65536' vram='65536' "
                       "vgamem='16384' heads='1' primary='yes'/>")
        xmlstr = xmlstr.replace("<model type='VIDEO' vram='16384' "
                                "heads='1'/>", video_model)
    else:
        xmlstr = xmlstr.replace("VIDEO", video)

    return xmlstr


# options: guestname, guestos, guestarch, nicdriver, hddriver,
#          imageformat, graphic, video, diskpath, seeksize, storage
def print_info(options, logger):
    logger.info("guestname: %s" % options[0])
    logger.info("%s, %s, %s(network), %s(disk), %s, %s, %s, %s(storage)" %
                (options[1], options[2], options[3], options[4],
                 options[5], options[6], options[7], options[10]))
#    logger.info("disk path: %s" % options[8])


def start_guest(conn, installtype, xmlstr, logger):
    if installtype == 'define':
        try:
            logger.info('define guest from xml description')
            domobj = conn.defineXML(xmlstr)

            time.sleep(3)
            logger.info('start installation guest ...')
            domobj.create()
        except libvirtError as e:
            logger.error("API error message: %s, error code is %s"
                         % (e.get_error_message(), e.get_error_code()))
            return False
    elif installtype == 'create':
        logger.info('create guest from xml description')
        try:
            domobj = conn.createXML(xmlstr, 0)
        except libvirtError as e:
            logger.error("API error message: %s, error code is %s"
                         % (e.get_error_message(), e.get_error_code()))
            return False
    else:
        logger.error("%s is not supported." % installtype)
        return False

    return True


def clean_xml(xmlstr):
    xmlstr = xmlstr.replace("KERNEL", "")
    xmlstr = xmlstr.replace("INITRD", "")
    xmlstr = xmlstr.replace("ks=KS", "")
    xmlstr = xmlstr.replace("dev=\"cdrom\"", "dev=\"hd\"")
    return xmlstr


def prepare_boot_guest(domobj, xmlstr, guestname, installtype, installmethod, logger, guestos=None, isofile=None):
    """ After guest installation is over, undefine the guest with
        bootting off cdrom, to define the guest to boot off harddisk.
    """
    if installmethod == "bootiso" or installmethod == "pxe":
        xmlstr = xmlstr.replace('<boot dev="cdrom"/>', '<boot dev="hd"/>')
        xmlstr = re.sub('<disk device="cdrom".*\n.*\n.*\n.*\n.*\n', '', xmlstr)
    elif installmethod == "net":
        xmlstr = re.sub("<kernel>.*</kernel>\n", "", xmlstr)
        xmlstr = re.sub("<initrd>.*</initrd>\n", "", xmlstr)
        xmlstr = re.sub("<cmdline>.*</cmdline>\n", "", xmlstr)
    elif installmethod == "iso":
        xmlstr = xmlstr.replace('<boot dev="cdrom"/>', '<boot dev="hd"/>')
        xmlstr = re.sub('<disk device="cdrom".*\n.*\n.*\n.*\n.*\n', '', xmlstr)
        xmlstr = re.sub("<kernel>.*</kernel>\n", "", xmlstr)
        xmlstr = re.sub("<initrd>.*</initrd>\n", "", xmlstr)
        xmlstr = re.sub('<cmdline>.*</cmdline>', '', xmlstr)
    elif installmethod == "http" or installmethod == "ftp":
        xmlstr = re.sub("<kernel>.*</kernel>\n", "", xmlstr)
        xmlstr = re.sub("<initrd>.*</initrd>\n", "", xmlstr)
        xmlstr = re.sub("<cmdline>.*</cmdline>\n", "", xmlstr)
    elif installmethod == "nfs":
        xmlstr = re.sub("<kernel>.*</kernel>\n", "", xmlstr)
        xmlstr = re.sub("<initrd>.*</initrd>\n", "", xmlstr)
        xmlstr = re.sub("<cmdline>.*</cmdline>\n", "", xmlstr)
        xmlstr = re.sub("<interface type='direct'>",
                        "<interface type='network'>",
                        xmlstr)
        xmlstr = re.sub("<source dev=.* mode='bridge'/>",
                        "<source network='default'/>",
                        xmlstr)
        xmlstr = re.sub("\n.*<target dev='macvtap0'/>", "", xmlstr)
        xmlstr = re.sub("<alias name=.*>\n", "", xmlstr)

    if guestos == "win10" or guestos == "win8u1":
        xmlstr = xmlstr.replace('/tmp/%s' % isofile.split('/')[-1], '/usr/share/virtio-win/virtio-win.iso')
    else:
        xmlstr = re.sub('<disk device="cdrom".*\n.*\n.*\n.*\n.*\n', '', xmlstr)

    if installtype != 'create':
        domobj.undefine()
        logger.info("undefine %s : \n" % guestname)
        time.sleep(10)

    time.sleep(5)
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
    time.sleep(3)
    try:
        domobj.create()
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        logger.error("fail to start domain %s" % guestname)
        return 1

    time.sleep(10)

    return 0


def wait_install(conn, guestname, xmlstr, installtype, installmethod, logger, timeout=8000, guestos=None, isofile=None):
    domobj = conn.lookupByName(guestname)
    interval = 0
    xmlstr_bak = xmlstr
    while interval < int(timeout):
        time.sleep(10)
        if installtype == 'define':
            state = domobj.info()[0]
            if state == libvirt.VIR_DOMAIN_SHUTOFF:
                logger.info("guest installaton of define type is complete.")
                logger.info("boot guest vm off harddisk")
                ret = prepare_boot_guest(domobj, xmlstr, guestname, installtype, installmethod, logger, guestos, isofile)
                if ret:
                    logger.info("booting guest vm off harddisk failed")
                    return False
                break
            else:
                interval += 10
                logger.info('%s seconds passed away...' % interval)
        elif installtype == 'create':
            guest_names = []
            ids = conn.listDomainsID()
            for id in ids:
                obj = conn.lookupByID(id)
                guest_names.append(obj.name())

            if guestname not in guest_names:
                logger.info("guest installation of create type is complete.")
                logger.info("define the vm and boot it up")
                ret = prepare_boot_guest(domobj, xmlstr, guestname, installtype, installmethod, logger, guestos, isofile)
                if ret:
                    logger.info("booting guest vm off harddisk failed")
                    return False
                break
            else:
                interval += 10
                logger.info('%s seconds passed away...' % interval)
        else:
            logger.error("%s is not supported." % installtype)
            return False

    if interval == timeout:
        logger.info("guest installation timeout: %ss" % timeout)
        return False
    else:
        logger.info("guest is booting up")

    # add to test
    mac = utils.get_dom_mac_addr(guestname)
    logger.info("MAC address: %s" % mac)
    count = 5
    while count:
        time.sleep(5)
        count -= 1
        ip = utils.mac_to_ip(mac, 180)
        if not ip:
            logger.info(str(count) + "s left")
        else:
            logger.info("Guest %s start successfully" % guestname)
            logger.info("IP address: %s" % ip)
            break

    if count == 0:
        logger.info("Guest %s start failed, restart guest again." % guestname)
        conn = libvirt.open()
        try:
            dom_list = conn.listAllDomains()
            dom_flag = 0
            for dom in dom_list:
                if dom.name() == guestname:
                    dom_flag = 1
                    if dom.isActive() == 1:
                        logger.debug("guest is active, reboot it.")
                        dom.reboot()
                    else:
                        logger.debug("guest exist but not start, start it.")
                        dom.create()

                    time.sleep(30)

            if not dom_flag:
                logger.debug("guest don't exist, define and start it.")
                dom = conn.defineXML()
                time.sleep(3)
                dom.create()
                time.sleep(20)
        except libvirtError as e:
            logger.error("API error message: %s, error code is %s"
                         % (e.get_error_message(), e.get_error_code()))
            logger.error("fail to start domain %s" % guestname)
            return False
    # end to test

    return True


# options: guestname, guestos, guestarch, nicdriver, hddriver,
#          imageformat, graphic, video, diskpath, seeksize
def prepare_env(options, logger):
    print_info(options, logger)
    clean_guest(options[0], logger)


def get_vmlinuz_initrd(ostree, xmlstr, logger):
    vmlinuzpath = os.path.join(ostree, 'isolinux/vmlinuz')
    initrdpath = os.path.join(ostree, 'isolinux/initrd.img')

    logger.debug("vmlinuz: %s" % vmlinuzpath)
    logger.debug("initrd: %s" % initrdpath)
    remove_vmlinuz_initrd(logger)
    urllib.request.urlretrieve(vmlinuzpath, VMLINUZ)
    urllib.request.urlretrieve(initrdpath, INITRD)

    logger.debug("Download to %s" % BOOT_DIR)

    xmlstr = xmlstr.replace('KERNEL', VMLINUZ)
    xmlstr = xmlstr.replace('INITRD', INITRD)

    return xmlstr


def remove_vmlinuz_initrd(logger):
    remove_all(VMLINUZ, logger)
    remove_all(INITRD, logger)
