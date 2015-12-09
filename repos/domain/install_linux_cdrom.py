#!/usr/bin/env python
# Install a linux domain from CDROM
# The iso file may be locked by other proces, and cause the failure of installation
import os
import sys
import re
import time
import commands
import shutil
import urllib

import libvirt
from libvirt import libvirtError

from src import sharedmod
from src import env_parser
from utils import utils

required_params = ('guestname', 'guestos', 'guestarch',)
optional_params = {
                   'memory': 1048576,
                   'vcpu': 1,
                   'disksize' : 10,
                   'diskpath' : '/var/lib/libvirt/images/libvirt-test-api',
                   'imageformat' : 'raw',
                   'hddriver' : 'virtio',
                   'nicdriver': 'virtio',
                   'macaddr': '52:54:00:97:e4:28',
                   'uuid': '05867c1a-afeb-300e-e55e-2673391ae080',
                   'type': 'define',
                   'xml': 'xmls/kvm_linux_guest_install_cdrom.xml',
                   'guestmachine': 'pc',
                   'networksource': 'default',
                   'bridgename': 'virbr0',
                   'graphic': "spice",
                   'disksymbol' : 'sdb'
                  }

VIRSH_QUIET_LIST = "virsh --quiet list --all|awk '{print $2}'|grep \"^%s$\""
VM_STAT = "virsh --quiet list --all| grep \"\\b%s\\b\"|grep off"
VM_DESTROY = "virsh destroy %s"
VM_UNDEFINE = "virsh undefine %s"

HOME_PATH = os.getcwd()

def prepare_cdrom(ostree, ks, guestname, cache_folder, logger):
    """ to customize boot.iso file to add kickstart
        file into it for automatic guest installation
    """
    ks_name = os.path.basename(ks)

    new_dir = os.path.join(cache_folder, guestname + "_folder")
    logger.info("creating a workshop folder for customizing custom.iso file")

    if  os.path.exists(new_dir):
        if os.path.isdir(new_dir):
            logger.info("the folder exists, remove it")
            shutil.rmtree(new_dir)
        else:
            os.remove(new_dir)

    os.makedirs(new_dir)
    logger.info("the directory is %s" % new_dir)

    boot_path = os.path.join(ostree, 'images/boot.iso')
    logger.info("the url of downloading boot.iso file is %s" % boot_path)

    urllib.urlretrieve(boot_path, '%s/boot.iso' % new_dir)[0]
    time.sleep(10)

    urllib.urlretrieve(ks, '%s/%s' % (new_dir, ks_name))[0]
    logger.info("the url of kickstart is %s" % ks)

    shutil.copy('utils/ksiso.sh', new_dir)
    src_path = os.getcwd()

    logger.debug("enter folder: %s" % new_dir)
    os.chdir(new_dir)
    shell_cmd = 'sh ksiso.sh %s' % ks_name

    logger.info("running command %s to making the custom.iso file" % shell_cmd)
    (status, text) = commands.getstatusoutput(shell_cmd)

    logger.debug(text)

    logger.debug("go back to original directory: %s" % src_path)
    os.chdir(src_path)


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
    except libvirtError as e:
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
    except libvirtError as e:
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


def install_linux_cdrom(params):
    """ install a new virtual machine """
    logger = params['logger']

    guestname = params.get('guestname')
    guestos = params.get('guestos')
    guestarch = params.get('guestarch')
    br = params.get('bridgename', 'virbr0')
    xmlstr = params['xml']

    logger.info("the name of guest is %s" % guestname)

    conn = sharedmod.libvirtobj['conn']
    check_domain_state(conn, guestname, logger)

    logger.info("the macaddress is %s" %
                params.get('macaddr', '52:54:00:97:e4:28'))

    hddriver = params.get('hddriver', 'virtio')
    diskpath = params.get('diskpath', '/var/lib/libvirt/images/libvirt-test-api')
    if hddriver != "lun" and hddriver != 'scsilun':
        logger.info("disk image is %s" % diskpath)
        seeksize = params.get('disksize', 10)
        imageformat = params.get('imageformat', 'raw')
        logger.info("create disk image with size %sG, format %s" % (seeksize, imageformat))
        disk_create = "qemu-img create -f %s %s %sG" % \
                       (imageformat, diskpath, seeksize)
        logger.debug("the command line of creating disk images is '%s'" % \
                       disk_create)
        (status, message) = commands.getstatusoutput(disk_create)
        if status != 0:
            logger.debug(message)
            logger.info("creating disk images file is fail")
            return 1


    os.chown(diskpath, 107, 107)
    logger.info("creating disk images file is successful.")

    if hddriver == 'virtio':
        xmlstr = xmlstr.replace('DEV', 'vda')
    elif hddriver == 'ide':
        xmlstr = xmlstr.replace('DEV', 'hda')
    elif hddriver == 'scsi':
        xmlstr = xmlstr.replace('DEV', 'sda')
    elif hddriver == "sata":
        xmlstr = xmlstr.replace("DEV", 'sda')
    elif hddriver == 'lun':
        xmlstr = xmlstr.replace("'lun'","'virtio'")
        xmlstr = xmlstr.replace('DEV','vda')
        xmlstr = xmlstr.replace('"file"','"block"')
        xmlstr = xmlstr.replace('"disk"','"lun"')
        tmp = params.get('diskpath', '/var/lib/libvirt/images')
        xmlstr = xmlstr.replace("file='%s'"% tmp, \
                                "dev='/dev/SDX'")
        disksymbol = params.get('disksymbol','sdb')
        xmlstr = xmlstr.replace('SDX',disksymbol)
        xmlstr = xmlstr.replace('device="cdrom" type="block">', 'device="cdrom" type="file">')
    elif hddriver == 'scsilun':
        xmlstr = xmlstr.replace("'scsilun'","'scsi'")
        xmlstr = xmlstr.replace('DEV','sda')
        xmlstr = xmlstr.replace('"file"','"block"')
        xmlstr = xmlstr.replace('"disk"','"lun"')
        tmp = params.get('diskpath', '/var/lib/libvirt/images')
        xmlstr = xmlstr.replace("file='%s'"% tmp, \
                                "dev='/dev/SDX'")
        disksymbol = params.get('disksymbol','sdb')
        xmlstr = xmlstr.replace('SDX',disksymbol)
        xmlstr = xmlstr.replace('device="cdrom" type="block">', 'device="cdrom" type="file">')

    graphic = params.get('graphic', 'spice')
    if graphic == 'spice':
        xmlstr = xmlstr.replace('vnc', 'spice')
    logger.info('the graphic type of VM is %s' % graphic)


    logger.info("get system environment information")
    envfile = os.path.join(HOME_PATH, 'global.cfg')
    logger.info("the environment file is %s" % envfile)

    os_arch = guestos + "_" + guestarch

    envparser = env_parser.Envparser(envfile)
    ostree = envparser.get_value("guest", os_arch)
    ks = envparser.get_value("guest", os_arch + "_http_ks")

    logger.debug('install source:\n    %s' % ostree)
    logger.debug('kisckstart file:\n    %s' % ks)

    if (ostree == 'http://'):
        logger.error("no os tree defined in %s for %s" % (envfile, os_arch))
        return 1

    logger.info('prepare installation...')
    cache_folder = envparser.get_value("variables", "domain_cache_folder")

    logger.info("begin to customize the custom.iso file")
    prepare_cdrom(ostree, ks, guestname, cache_folder, logger)

    bootcd = '%s/custom.iso' % \
                       (os.path.join(cache_folder, guestname + "_folder"))
    xmlstr = xmlstr.replace('CUSTOMISO', bootcd)
    logger.debug('dump installation guest xml:\n%s' % xmlstr)

    installtype = params.get('type', 'define')
    if installtype == 'define':
        logger.info('define guest from xml description')
        try:
            domobj = conn.defineXML(xmlstr)
        except libvirtError as e:
            logger.error("API error message: %s, error code is %s"
                         % (e.message, e.get_error_code()))
            logger.error("fail to define domain %s" % guestname)
            return 1

        logger.info('start installation guest ...')

        try:
            domobj.create()
        except libvirtError as e:
            logger.error("API error message: %s, error code is %s"
                         % (e.message, e.get_error_code()))
            logger.error("fail to start domain %s" % guestname)
            return 1
    elif installtype == 'create':
        logger.info('create guest from xml description')
        try:
            domobj = conn.createXML(xmlstr, 0)
        except libvirtError as e:
            logger.error("API error message: %s, error code is %s"
                         % (e.message, e.get_error_code()))
            logger.error("fail to define domain %s" % guestname)
            return 1

    interval = 0
    while(interval < 2400):
        time.sleep(10)
        if installtype == 'define':
            state = domobj.info()[0]
            if(state == libvirt.VIR_DOMAIN_SHUTOFF):
                logger.info("guest installaton of define type is complete.")
                logger.info("boot guest vm off harddisk")
                ret = prepare_boot_guest(
                    domobj, xmlstr, guestname, installtype, logger)
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
                ret = prepare_boot_guest(
                    domobj, xmlstr, guestname, installtype, logger)
                if ret:
                    logger.info("booting guest vm off harddisk failed")
                    return 1
                break
            else:
                interval += 10
                logger.info('%s seconds passed away...' % interval)

    if interval == 2400:
        if 'rhel3u9' in guestname:
            logger.info(
                "guest installaton will be destoryed forcelly for rhel3u9 guest")
            domobj.destroy()
            logger.info("boot guest vm off harddisk")
            ret = prepare_boot_guest(
                domobj, xmlstr, guestname, installtype, logger)
            if ret:
                logger.info("booting guest vm off harddisk failed")
                return 1
        else:
            logger.info("guest installation timeout 2400s")
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


def install_linux_cdrom_clean(params):
    """ clean testing environment """
    logger = params['logger']
    guestname = params.get('guestname')

    diskpath = params.get(
        'diskpath',
        '/var/lib/libvirt/images/libvirt-test-api')

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
                (status, output) = commands.getstatusoutput(
                    VM_UNDEFINE % guestname)
                if status:
                    logger.error("failed to undefine guest %s" % guestname)
                    logger.error("%s" % output)
        else:
            (status, output) = commands.getstatusoutput(VM_UNDEFINE % guestname)
            if status:
                logger.error("failed to undefine guest %s" % guestname)
                logger.error("%s" % output)
    if os.path.exists(diskpath):
        os.remove(diskpath)

    envfile = os.path.join(HOME_PATH, 'global.cfg')
    envparser = env_parser.Envparser(envfile)
    cache_folder = envparser.get_value("variables", "domain_cache_folder")

    if os.path.exists(cache_folder + '/' + guestname + "_folder"):
        shutil.rmtree(cache_folder + '/' + guestname + "_folder")

    guest_dir = os.path.join(HOME_PATH, guestname)
    if os.path.exists(guest_dir):
        shutil.rmtree(guest_dir)
