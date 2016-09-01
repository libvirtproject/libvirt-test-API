#!/usr/bin/env python
# Install a linux domain from pxe

import os
import re
import time
import commands
import shutil

import libvirt
from libvirt import libvirtError

from src import sharedmod
from src import env_parser
from utils import utils

required_params = ('guestname', 'guestos', 'guestarch',)
optional_params = {'memory': 1048576,
                   'vcpu': 1,
                   'disksize': 10,
                   'diskpath': '/var/lib/libvirt/images/libvirt-test-api',
                   'imageformat': 'qcow2',
                   'hddriver': 'virtio',
                   'nicdriver': 'virtio',
                   'macaddr': '52:54:00:97:e4:28',
                   'type': 'define',
                   'xml': 'xmls/kvm_linux_guest_install_pxe.xml',
                   'graphic': "spice",
                   'video': 'qxl',
                   'guestmachine': 'pc',
                   'rhelnewest': '', }

VIRSH_QUIET_LIST = "virsh --quiet list --all|awk '{print $2}'|grep \"^%s$\""
VM_STAT = "virsh --quiet list --all| grep \"\\b%s\\b\"|grep off"
VM_DESTROY = "virsh destroy %s"
VM_UNDEFINE = "virsh undefine %s"

HOME_PATH = os.getcwd()

TFTPPATH = "/var/lib/tftpboot"


def clean_env(diskpath, logger):
    if os.path.exists(diskpath):
        os.remove(diskpath)

    if os.path.exists(TFTPPATH + '/pxelinux.cfg/default'):
        os.remove(TFTPPATH + '/pxelinux.cfg/default')

    cmd = "virsh net-list --all | grep \'pxeboot\'"
    (status, output) = commands.getstatusoutput(cmd)
    if not status:
        logger.info("remove network pxeboot")
        cmd = "virsh net-destroy pxeboot"
        (status, output) = commands.getstatusoutput(cmd)
        if status:
            logger.error("failed to destroy network pxeboot")
            logger.error("%s" % output)
        else:
            cmd = "virsh net-undefine pxeboot"
            (status, output) = commands.getstatusoutput(cmd)
            if status:
                logger.error("failed to undefine network pxeboot")
                logger.error("%s" % output)


def prepare_install(default_file, logger):
    if not os.path.exists(TFTPPATH + "/pxelinux.cfg"):
        logger.info("%s not exists, create it" % (TFTPPATH + "/pxelinux.cfg"))
        os.makedirs(TFTPPATH + "/pxelinux.cfg", mode=0777)
    else:
        os.chmod(TFTPPATH + "/pxelinux.cfg", 0777)
    # Get rid of selinux problem
    os.system("restorecon -Rv %s" % TFTPPATH)
    bootp_file = TFTPPATH + "/pxelinux.0"
    if not os.path.exists(bootp_file):
        shutil.copy("/usr/share/syslinux/pxelinux.0", TFTPPATH)

    cmd = "wget " + default_file + " -P " + TFTPPATH + "/pxelinux.cfg/"
    logger.info("%s" % cmd)
    (status, out) = commands.getstatusoutput(cmd)

    xmlpath = os.path.join(HOME_PATH, 'repos/domain/xmls/pxeboot.xml')
    cmd = "virsh net-define %s" % xmlpath
    logger.info("%s" % cmd)
    (status, text) = commands.getstatusoutput(cmd)

    cmd = "virsh net-start pxeboot"
    logger.info("%s" % cmd)
    (status, text) = commands.getstatusoutput(cmd)


def prepare_boot_guest(domobj, xmlstr, guestname, installtype, logger):
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
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        logger.error("fail to define domain %s" % guestname)
        return 1

    logger.info("define guest %s " % guestname)
    logger.debug("the xml description of guest booting off harddisk is %s" %
                 xmlstr)

    logger.info('boot guest up ...')

    try:
        domobj.create()
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
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


def install_linux_pxe(params):
    """ install a new virtual machine """
    logger = params['logger']

    guestname = params.get('guestname')
    guestos = params.get('guestos')
    guestarch = params.get('guestarch')
    xmlstr = params['xml']

    graphic = params.get('graphic', 'spice')
    xmlstr = xmlstr.replace('GRAPHIC', graphic)

    video = params.get('video', 'qxl')
    if video == "qxl":
        video_model = "<model type='qxl' ram='65536' vram='65536' vgamem='16384' heads='1' primary='yes'/>"
        xmlstr = xmlstr.replace("<model type='cirrus' vram='16384' heads='1'/>", video_model)

    conn = sharedmod.libvirtobj['conn']
    check_domain_state(conn, guestname, logger)

    diskpath = params.get('diskpath', '/var/lib/libvirt/images/libvirt-test-api')
    clean_env(diskpath, logger)
    seeksize = params.get('disksize', 10)
    imageformat = params.get('imageformat', 'qcow2')
    disk_create = "qemu-img create -f %s %s %sG" % (imageformat,
                                                    diskpath, seeksize)
    logger.debug("the command line of creating disk images is '%s'" %
                 disk_create)

    (status, message) = commands.getstatusoutput(disk_create)
    if status != 0:
        logger.debug(message)
        return 1

    os.chown(diskpath, 107, 107)

    hddriver = params.get('hddriver', 'virtio')
    if hddriver == 'virtio':
        xmlstr = xmlstr.replace('DEV', 'vda')
    elif hddriver == 'ide':
        xmlstr = xmlstr.replace('DEV', 'hda')
    elif hddriver == 'scsi':
        xmlstr = xmlstr.replace('DEV', 'sda')

    nicdriver = params.get('nicdriver', 'virtio')

    logger.info("guestname: %s" % guestname)
    logger.info("%s, %s, %s(network), %s(disk), %s, %s, %s" %
                (guestos, guestarch, nicdriver, hddriver, imageformat,
                 graphic, video))
    logger.info("disk path: %s" % diskpath)

    logger.info("get system environment information")
    envfile = os.path.join(HOME_PATH, 'global.cfg')
    logger.info("the environment file is %s" % envfile)

    os_arch = guestos + "_" + guestarch

    envparser = env_parser.Envparser(envfile)
    rhelnewest = params.get("rhelnewest", "")
    if rhelnewest is not None and "RHEL-7" in rhelnewest:
        default_file = envparser.get_value("guest", "rhel7_newest_pxe_default")
    else:
        default_file = envparser.get_value("guest", os_arch + "_pxe_default")
    logger.debug('default file:\n    %s' % default_file)

    logger.info("begin to prepare network")
    prepare_install(default_file, logger)

    logger.debug('dump installation guest xml:\n%s' % xmlstr)

    installtype = params.get('type', 'define')
    if installtype == 'define':
        logger.info('define guest from xml description')
        try:
            domobj = conn.defineXML(xmlstr)
        except libvirtError, e:
            logger.error("API error message: %s, error code is %s"
                         % (e.message, e.get_error_code()))
            logger.error("fail to define domain %s" % guestname)
            return 1

        logger.info('start installation guest ...')

        try:
            domobj.create()
        except libvirtError, e:
            logger.error("API error message: %s, error code is %s"
                         % (e.message, e.get_error_code()))
            logger.error("fail to start domain %s" % guestname)
            return 1
    elif installtype == 'create':
        logger.info('create guest from xml description')
        try:
            domobj = conn.createXML(xmlstr, 0)
        except libvirtError, e:
            logger.error("API error message: %s, error code is %s"
                         % (e.message, e.get_error_code()))
            logger.error("fail to define domain %s" % guestname)
            return 1

    interval = 0
    while(interval < 8000):
        time.sleep(10)
        if installtype == 'define':
            state = domobj.info()[0]
            if(state == libvirt.VIR_DOMAIN_SHUTOFF):
                logger.info("guest installaton of define type is complete.")
                logger.info("boot guest vm off harddisk")
                ret = prepare_boot_guest(domobj, xmlstr, guestname, installtype, logger)
                if ret:
                    logger.info("booting guest vm off harddisk failed")
                    return 1
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
                ret = prepare_boot_guest(domobj, xmlstr, guestname, installtype, logger)
                if ret:
                    logger.info("booting guest vm off harddisk failed")
                    return 1
                break
            else:
                interval += 10
                logger.info('%s seconds passed away...' % interval)

    if interval == 8000:
        if 'rhel3u9' in guestname:
            logger.info("guest installaton will be destoryed forcelly for rhel3u9 guest")
            domobj.destroy()
            logger.info("boot guest vm off harddisk")
            ret = prepare_boot_guest(domobj, xmlstr, guestname, installtype, logger)
            if ret:
                logger.info("booting guest vm off harddisk failed")
                return 1
        else:
            logger.info("guest installation timeout 8000s")
            return 1
    else:
        logger.info("guest is booting up")

    logger.info("get the mac address of vm %s" % guestname)
    mac = utils.get_dom_mac_addr(guestname)
    logger.info("the mac address of vm %s is %s" % (guestname, mac))

    timeout = 300

    while timeout:
        time.sleep(10)
        timeout -= 10

        ip = utils.mac_to_ip(mac, 180, "virbr5")

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


def install_linux_pxe_clean(params):
    """ clean testing environment """
    logger = params['logger']
    guestname = params.get('guestname')

    diskpath = params.get('diskpath', '/var/lib/libvirt/images/libvirt-test-api')

    (status, output) = commands.getstatusoutput(VIRSH_QUIET_LIST % guestname)
    if not status:
        logger.info("remove guest %s, and its disk image file" % guestname)
        (status, output) = commands.getstatusoutput(VM_STAT % guestname)
        if status:
            (status, output) = commands.getstatusoutput(VM_DESTROY % guestname)
            if status:
                logger.error("failed to destroy guest %s" % guestname)
                logger.error("%s" % output)
            else:
                (status, output) = commands.getstatusoutput(VM_UNDEFINE % guestname)
                if status:
                    logger.error("failed to undefine guest %s" % guestname)
                    logger.error("%s" % output)
        else:
            (status, output) = commands.getstatusoutput(VM_UNDEFINE % guestname)
            if status:
                logger.error("failed to undefine guest %s" % guestname)
                logger.error("%s" % output)

    clean_env(diskpath, logger)
