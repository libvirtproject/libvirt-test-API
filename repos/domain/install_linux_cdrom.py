#!/usr/bin/env python
# Install a linux domain from CDROM
# The iso file may be locked by other proces, and cause the failure of installation
import os
import re
import time
import commands
import shutil
import urllib

import libvirt
from libvirt import libvirtError
from src.exception import TestError

from src import sharedmod
from src import env_parser
from utils import utils

required_params = ('guestname', 'guestos', 'guestarch',)
optional_params = {
                   'memory': 1048576,
                   'vcpu': 1,
                   'disksize': 10,
                   'diskpath': '/var/lib/libvirt/images/libvirt-test-api',
                   'imageformat': 'raw',
                   'hddriver': 'virtio',
                   'nicdriver': 'virtio',
                   'macaddr': '52:54:00:97:e4:28',
                   'uuid': '05867c1a-afeb-300e-e55e-2673391ae080',
                   'type': 'define',
                   'xml': 'xmls/kvm_linux_guest_install_cdrom.xml',
                   'guestmachine': 'pc',
                   'networksource': 'default',
                   'bridgename': 'virbr0',
                   'graphic': "spice",
                   'video': 'qxl',
                   'disksymbol': 'sdb',
                   'rhelnewest': '',
}

VIRSH_QUIET_LIST = "virsh --quiet list --all|awk '{print $2}'|grep \"^%s$\""
VM_STAT = "virsh --quiet list --all| grep \"\\b%s\\b\"|grep off"
VM_DESTROY = "virsh destroy %s"
VM_UNDEFINE = "virsh undefine %s"

HOME_PATH = os.getcwd()


def mk_kickstart_iso(kscfg, guestos, logger):
    def remove_all(path):
        """rm -rf"""
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path)
        elif os.path.exists(path):
            os.remove(path)

    cwd = os.getcwd()
    boot_iso = "boot.iso"
    custom_iso = "custom.iso"
    boot_iso_dir = "/mnt/boot_iso_dir"
    custom_iso_dir = "/mnt/new"
    kernel_args = os.getenv('kernel_args', '')

    logger.debug("clean up in case of previous failure")
    remove_all(boot_iso_dir)
    remove_all(custom_iso_dir)

    logger.debug("create work directories")
    os.makedirs(boot_iso_dir)

    logger.debug("mount " + boot_iso)
    (ret, msg) = commands.getstatusoutput("mount -t iso9660 -o loop %s %s"
                                          % (boot_iso, boot_iso_dir))
    if ret != 0:
        raise RuntimeError('Failed to start making custom iso: ' + msg)

    logger.debug("copy original iso files to custom work directory")
    shutil.copytree(boot_iso_dir, custom_iso_dir)

    for root, dirs, files in os.walk(custom_iso):
        for i in dirs:
            os.chmod(os.path.join(root, i), 511)  # DEC 511 == OCT 777
        for i in files:
            os.chmod(os.path.join(root, i), 511)

    (ret, msg) = commands.getstatusoutput("umount %s" % boot_iso_dir)
    if ret != 0:
        raise RuntimeError('Failed umounting boot iso: ' + msg)

    vlmid = commands.getoutput("isoinfo -d -i %s |grep 'Volume id:'" % boot_iso)
    logger.debug("vlmid :" + vlmid)

    logger.debug("editing config files")
    new_cfg_filename = 'tmp_cfg'
    new_cfg = open('tmp_cfg', 'w')

    if "ppc" in vlmid:
        logger.debug("edit yaboot.conf and add kickstart entry")
        old_cfg_filename = custom_iso_dir + "/etc/yaboot.conf"
        old_cfg = open(old_cfg_filename, 'r')

        timeout_found = append_found = False
        # change timeout and  add kickstart entry
        for line in old_cfg:
            if not timeout_found and re.search('timeout', line):
                timeout_found = True
                line = 'timeout=5\n'
            if not append_found and re.search('append', line):
                append_found = True
                line = ('append= "root=live:CDLABEL=%s ks=cdrom:/%s "\n'
                        % (vlmid, kscfg))
            new_cfg.write(line)

        new_cfg.close()
        old_cfg.close()

        remove_all(old_cfg_filename)
        shutil.move(new_cfg_filename, old_cfg_filename)
        os.chdir(custom_iso_dir)
        mkisofs_command = ('mkisofs -R -V "%s" -sysid PPC -chrp-boot '
                           '-U -prep-boot ppc/chrp/yaboot -hfs-bless ppc/mac -no-desktop '
                           '-allow-multidot -volset 4 -volset-size 1 -volset-seqno 1 '
                           '-hfs-volid 4 -o %s/%s .' % (vlmid, cwd, custom_iso))
    else:
        logger.debug("copy kickstart to custom work directory")
        old_kscfg, new_kscfg = open(kscfg, 'r'), open(custom_iso_dir + '/' + kscfg, 'w')
        network_configed = False
        for line in old_kscfg:
            if line.startswith('network'):
                network_configed = True
            if '%post' in line and kscfg.startswith('ks-rhel7'):
                logger.debug("setting qemu-guest-agent autostart")
                line = '%post \nsystemctl enable qemu-guest-agent.service\n'
            new_kscfg.write(line)
            # Always use traditional naming style and enable eth0
        if not network_configed:
            new_kscfg.write('network --bootproto=dhcp --device=eth0 --onboot=on\n')

        old_kscfg.close()
        new_kscfg.close()
        remove_all(kscfg)

        logger.debug("edit isolinux.cfg and add kickstart entry")
        old_cfg_filename = custom_iso_dir + "/isolinux/isolinux.cfg"
        old_cfg = open(old_cfg_filename, 'r')

        default_found = timeout_found = False
        for line in old_cfg:
            if not default_found and re.search('default', line):
                default_found = True
                line = "default custom_ks\n"
            if not timeout_found and re.search('timeout', line):
                timeout_found = True
                line = "timeout 5\n"
            new_cfg.write(line)

        #use different isolinux.cfg for rhel7 ,rhel6 and rhel5 guest
        if 'rhel7' in guestos:
            # Disable new style of network interface naming on rhel7
            kernel_args = kernel_args + ' net.ifnames=0'

            new_cfg.write('label custom_ks\n'
                          'kernel vmlinuz\n'
                          'append initrd=initrd.img ks=cdrom:sr0:/%s '
                          'repo=cdrom:sr0 ramdisk_size=20000 %s' % (kscfg, kernel_args))
        else:
            new_cfg.write('label custom_ks\n'
                          'kernel vmlinuz\n'
                          'append initrd=initrd.img ks=cdrom:/%s '
                          'ramdisk_size=20000 %s' % (kscfg, kernel_args))

        new_cfg.close()
        old_cfg.close()

        remove_all(old_cfg_filename)
        shutil.move(new_cfg_filename, old_cfg_filename)
        os.chdir(custom_iso_dir)
        mkisofs_command = ('mkisofs -R -b '
                           'isolinux/isolinux.bin -no-emul-boot '
                           '-boot-load-size 4 -boot-info-table -o %s/%s .'
                           % (cwd, custom_iso))

    (ret, msg) = commands.getstatusoutput(mkisofs_command)
    if ret != 0:
        raise RuntimeError("Failed to make custom_iso, error %d: %s!" % (ret, msg))

    # clean up
    remove_all(boot_iso_dir)
    remove_all(custom_iso_dir)


def prepare_cdrom(ostree, kscfg, guestname, guestos, cache_folder, logger):
    """ to customize boot.iso file to add kickstart
        file into it for automatic guest installation
    """
    ks_name = os.path.basename(kscfg)

    new_dir = os.path.join(cache_folder, guestname + "_folder")
    logger.info("creating a workshop folder for customizing custom.iso file")

    if os.path.exists(new_dir):
        if os.path.isdir(new_dir):
            logger.info("the folder exists, remove it")
            shutil.rmtree(new_dir)
        else:
            os.remove(new_dir)

    os.makedirs(new_dir)
    logger.info("the directory is %s" % new_dir)

    boot_path = os.path.join(ostree, 'images/boot.iso')
    logger.info("the url of downloading boot.iso file is %s" % boot_path)

    urllib.urlretrieve(boot_path, '%s/boot.iso' % new_dir)
    time.sleep(10)

    urllib.urlretrieve(kscfg, '%s/%s' % (new_dir, ks_name))
    logger.info("the url of kickstart is %s" % kscfg)

    src_path = os.getcwd()

    logger.debug("enter folder: %s" % new_dir)
    os.chdir(new_dir)

    logger.info("making the custom.iso file")
    try:
        mk_kickstart_iso(ks_name, guestos, logger)
    except EnvironmentError as err:
        logger.error("Error: [%d]: %s: %s!" % (err.errno, err.strerror, err.filename))
        raise TestError()
    except RuntimeError as err:
        logger.error("Error: %s!" % (err.message))
        raise TestError()

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


def set_xml(xmlstr, hddriver, diskpath, logger):
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
        xmlstr = xmlstr.replace("file='%s'" % diskpath, "dev='/dev/SDX'")
        disksymbol = params.get('disksymbol', 'sdb')
        xmlstr = xmlstr.replace('SDX', disksymbol)
        xmlstr = xmlstr.replace('device="cdrom" type="block">', 'device="cdrom" type="file">')
    elif hddriver == 'scsilun':
        xmlstr = xmlstr.replace("'scsilun'", "'scsi'")
        xmlstr = xmlstr.replace('DEV', 'sda')
        xmlstr = xmlstr.replace('"file"', '"block"')
        xmlstr = xmlstr.replace('"disk"', '"lun"')
        xmlstr = xmlstr.replace("file='%s'" % diskpath, "dev='/dev/SDX'")
        disksymbol = params.get('disksymbol', 'sdb')
        xmlstr = xmlstr.replace('SDX', disksymbol)
        xmlstr = xmlstr.replace('device="cdrom" type="block">', 'device="cdrom" type="file">')

    return xmlstr


def install_linux_cdrom(params):
    """ install a new virtual machine """
    logger = params['logger']

    guestname = params.get('guestname')
    logger.info("guestname: %s" % guestname)

    guestos = params.get('guestos')
    logger.info("guestos: %s" % guestos)

    guestarch = params.get('guestarch')
    logger.info("guestarch: %s" % guestarch)

    bridge = params.get('bridgename', 'virbr0')
    xmlstr = params['xml']

    conn = sharedmod.libvirtobj['conn']
    check_domain_state(conn, guestname, logger)

    hddriver = params.get('hddriver', 'virtio')
    logger.info("hddriver: %s" % hddriver)

    diskpath = params.get('diskpath', '/var/lib/libvirt/images/libvirt-test-api')
    logger.info("diskpath: %s" % diskpath)

    if hddriver != "lun" and hddriver != 'scsilun':
        logger.info("disk image is %s" % diskpath)
        seeksize = params.get('disksize', 10)
        imageformat = params.get('imageformat', 'raw')
        logger.info("create disk image with size %sG, format %s" % (seeksize, imageformat))
        disk_create = ("qemu-img create -f %s %s %sG"
                       % (imageformat, diskpath, seeksize))
        logger.debug("the command line of creating disk images is '%s'"
                     % disk_create)
        (status, message) = commands.getstatusoutput(disk_create)
        if status != 0:
            logger.debug(message)
            logger.info("creating disk images file is fail")
            return 1

    os.chown(diskpath, 107, 107)
    logger.info("creating disk images file is successful.")

    xmlstr = set_xml(xmlstr, hddriver, diskpath, logger)

    graphic = params.get('graphic', 'spice')
    logger.info('graphical: %s' % graphic)
    xmlstr = xmlstr.replace('GRAPHIC', graphic)

    video = params.get('video', 'qxl')
    logger.info("video: %s" % video)
    if video == "qxl":
        video_model = "<model type='qxl' ram='65536' vram='65536' vgamem='16384' heads='1' primary='yes'/>"
        xmlstr = xmlstr.replace("<model type='cirrus' vram='16384' heads='1'/>", video_model)

    logger.info("get system environment information")
    envfile = os.path.join(HOME_PATH, 'global.cfg')
    logger.info("the environment file is %s" % envfile)
    envparser = env_parser.Envparser(envfile)

    rhelnewest = params.get('rhelnewest')
    logger.info("rhel newest: %s", rhelnewest)
    if rhelnewest is not None and "RHEL-7" in rhelnewest:
        ostree = rhelnewest + "/x86_64/os"
        kscfg = envparser.get_value("guest", "rhel7_newest_http_ks")
    else:
        os_arch = guestos + "_" + guestarch
        ostree = envparser.get_value("guest", os_arch)
        kscfg = envparser.get_value("guest", os_arch + "_http_ks")

    logger.info('install source:    %s' % ostree)
    logger.info('kisckstart file:    %s' % kscfg)

    if ostree == 'http://':
        logger.error("no os tree defined in %s for %s" % (envfile, os_arch))
        return 1

    cache_folder = envparser.get_value("variables", "domain_cache_folder")
    logger.info("begin to customize the custom.iso file")
    try:
        prepare_cdrom(ostree, kscfg, guestname, guestos, cache_folder, logger)
    except TestError, err:
        logger.error("Failed to prepare boot cdrom!")
        return 1

    bootcd = ('%s/custom.iso'
              % (os.path.join(cache_folder, guestname + "_folder")))

    xmlstr = xmlstr.replace('CUSTOMISO', bootcd)
    logger.debug('dump installation guest xml:\n%s' % xmlstr)

    installtype = params.get('type', 'define')
    if installtype == 'define':
        logger.info('define guest from xml description')
        try:
            logger.info('define guest from xml description')
            domobj = conn.defineXML(xmlstr)

            logger.info('start installation guest ...')
            domobj.create()
        except libvirtError, e:
            logger.error("API error message: %s, error code is %s"
                         % (e.message, e.get_error_code()))
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
    while interval < 8000:
        time.sleep(10)
        if installtype == 'define':
            state = domobj.info()[0]
            if state == libvirt.VIR_DOMAIN_SHUTOFF:
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

    if interval == 8000:
        if 'rhel3u9' in guestname:
            logger.info(
                "guest installaton will be destoryed forcelly for rhel3u9 guest")
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

        ipaddr = utils.mac_to_ip(mac, 180, bridge)

        if not ipaddr:
            logger.info(str(timeout) + "s left")
        else:
            logger.info("vm %s power on successfully" % guestname)
            logger.info("the ip address of vm %s is %s" % (guestname, ipaddr))
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
