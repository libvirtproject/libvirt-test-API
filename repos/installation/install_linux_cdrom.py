#!/usr/bin/env python
# Install a linux domain from CDROM
# The iso file may be locked by other proces, and cause the failure of installation
import os
import re
import time
import shutil
import urllib

import libvirt
from libvirt import libvirtError
from src.exception import TestError

from src import sharedmod
from src import env_parser
from utils import utils, process
from repos.domain import domain_common

required_params = ('guestname', 'guestos', 'guestarch',)
optional_params = {
                   'memory': 2097152,
                   'vcpu': 2,
                   'disksize': 14,
                   'diskpath': '/var/lib/libvirt/images/libvirt-test-api',
                   'imageformat': 'qcow2',
                   'qcow2version': 'v3',
                   'hddriver': 'virtio',
                   'nicdriver': 'virtio',
                   'macaddr': '52:54:00:97:e4:28',
                   'uuid': '7c502278-af7d-4c5a-9a35-1c79ebdd974b',
                   'type': 'define',
                   'xml': 'xmls/kvm_linux_guest_install_cdrom_ppc.xml',
                   'guestmachine': 'pseries',
                   'networksource': 'default',
                   'bridgename': 'virbr0',
                   'graphic': "spice",
                   'video': 'qxl',
                   'disksymbol': 'sdb',
                   'rhelnewest': '',
                   'rhelalt': '',
}

HOME_PATH = os.getcwd()


# bootload file is processed due to different arch.
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
    cmd = "mount -t iso9660 -o loop %s %s" % (boot_iso, boot_iso_dir)
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status != 0:
        raise RuntimeError('Failed to start making custom iso: ' + ret.stdout)

    logger.debug("copy original iso files to custom work directory")
    shutil.copytree(boot_iso_dir, custom_iso_dir)

    for root, dirs, files in os.walk(custom_iso):
        for i in dirs:
            os.chmod(os.path.join(root, i), 511)  # DEC 511 == OCT 777
        for i in files:
            os.chmod(os.path.join(root, i), 511)

    cmd = "umount %s" % boot_iso_dir
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status != 0:
        raise RuntimeError('Failed umounting boot iso: ' + ret.stdout)

    cmd = "isoinfo -d -i %s |grep 'Volume id:'" % boot_iso
    ret = process.run(cmd, shell=True, ignore_status=True)
    vlmid = ret.stdout.split(":")[1]
    logger.debug("vlmid :" + vlmid)

    logger.debug("editing config files")
    new_cfg_filename = 'tmp_cfg'
    new_cfg = open('tmp_cfg', 'w')

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

    # yaboot.conf is only owned by rhel6_ppc, rhel7_ppc has no this file
    if "PBOOT" in vlmid:
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
                line = ('\tappend= "root=live:CDLABEL=%s ks=cdrom:/%s "\n' % (vlmid, kscfg))
            new_cfg.write(line)

        if not append_found:
            lastline = ('\tappend= "root=live:CDLABEL=%s ks=cdrom:/%s "\n' % (vlmid, kscfg))
            new_cfg.write(lastline)

        new_cfg.close()
        old_cfg.close()

        remove_all(old_cfg_filename)
        shutil.move(new_cfg_filename, old_cfg_filename)
        os.chdir(custom_iso_dir)
        mkisofs_command = ('mkisofs -R -V "%s" -sysid PPC -chrp-boot '
                           '-U -prep-boot ppc/ppc64/initrd.img -hfs-bless ppc/mac -no-desktop '
                           '-allow-multidot -volset 4 -volset-size 1 -volset-seqno 1 '
                           '-hfs-volid 4 -o %s/%s .' % (vlmid, cwd, custom_iso))

    # grub.cfg is needed modified on rhel7_ppc, there are no isolinx.cfg on ppc
    elif "ppc" in vlmid:
        logger.debug("edit grub.cfg and add kickstart entry")
        old_cfg_filename = custom_iso_dir + "/boot/grub/grub.cfg"
        old_cfg = open(old_cfg_filename, 'r')
        for line in old_cfg:
            if re.search(r'linux /ppc/ppc64/vmlinuz  ro', line):
                if 'rhel7' in guestos:
                    line = line.replace('ro', 'inst.repo=cdrom:sr0 inst.ks=cdrom:sr0:/%s ro' % kscfg)
                else:
                    line = line.replace('ro', 'inst.ks=cdrom:/%s ro' % kscfg)
            new_cfg.write(line)

        new_cfg.close()
        old_cfg.close()

        remove_all(old_cfg_filename)
        shutil.move(new_cfg_filename, old_cfg_filename)
        os.chdir(custom_iso_dir)

        mkisofs_command = ('mkisofs -R -V "%s" -sysid PPC -chrp-boot '
                           '-U -prep-boot ppc/ppc64/initrd.img -hfs-bless ppc/mac -no-desktop '
                           '-allow-multidot -volset 4 -volset-size 1 -volset-seqno 1 '
                           '-hfs-volid 4 -o %s/%s .' % (vlmid, cwd, custom_iso))

    else:
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

        # use different isolinux.cfg for rhel7 ,rhel6 and rhel5 guest
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

    ret = process.run(mkisofs_command, shell=True, ignore_status=True)
    if ret.exit_status != 0:
        raise RuntimeError("Failed to make custom_iso, error %d: %s!" % (ret.exit_status, ret.stdout))

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
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
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


def install_linux_cdrom(params):
    """ install a new virtual machine """
    logger = params['logger']

    guestname = params.get('guestname')
    guestos = params.get('guestos')
    guestarch = params.get('guestarch')
    bridge = params.get('bridgename', 'virbr0')
    xmlstr = params['xml']
    nicdriver = params.get('nicdriver', 'virtio')
    hddriver = params.get('hddriver', 'virtio')
    diskpath = params.get('diskpath', '/var/lib/libvirt/images/libvirt-test-api')
    seeksize = params.get('disksize', 14)
    imageformat = params.get('imageformat', 'raw')
    graphic = params.get('graphic', 'spice')
    video = params.get('video', 'qxl')
    installtype = params.get('type', 'define')

    logger.info("guestname: %s" % guestname)
    params_info = "%s, %s, " % (guestos, guestarch)
    params_info += "%s(network), %s(disk), " % (nicdriver, hddriver)
    params_info += "%s, %s, " % (imageformat, graphic)
    params_info += "%s, %s(storage)" % (video, 'local')
    logger.info("%s" % params_info)

    conn = sharedmod.libvirtobj['conn']
    check_domain_state(conn, guestname, logger)

    if hddriver != "lun" and hddriver != 'scsilun':
        logger.info("disk image is %s" % diskpath)
        logger.info("create disk image with size %sG, format %s" % (seeksize, imageformat))
        disk_create = ("qemu-img create -f %s %s %sG"
                       % (imageformat, diskpath, seeksize))
        logger.debug("the command line of creating disk images is '%s'"
                     % disk_create)
        ret = process.run(disk_create, shell=True, ignore_status=True)
        if ret.exit_status != 0:
            logger.debug(ret.stdout)
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
        xmlstr = xmlstr.replace("'lun'", "'virtio'")
        xmlstr = xmlstr.replace('DEV', 'vda')
        xmlstr = xmlstr.replace('"file"', '"block"')
        xmlstr = xmlstr.replace('"disk"', '"lun"')
        tmp = params.get('diskpath', '/var/lib/libvirt/images')
        xmlstr = xmlstr.replace("file='%s'" % tmp,
                                "dev='/dev/SDX'")
        disksymbol = params.get('disksymbol', 'sdb')
        xmlstr = xmlstr.replace('SDX', disksymbol)
        xmlstr = xmlstr.replace('device="cdrom" type="block">', 'device="cdrom" type="file">')
    elif hddriver == 'scsilun':
        xmlstr = xmlstr.replace("'scsilun'", "'scsi'")
        xmlstr = xmlstr.replace('DEV', 'sda')
        xmlstr = xmlstr.replace('"file"', '"block"')
        xmlstr = xmlstr.replace('"disk"', '"lun"')
        tmp = params.get('diskpath', '/var/lib/libvirt/images')
        xmlstr = xmlstr.replace("file='%s'" % tmp,
                                "dev='/dev/SDX'")
        disksymbol = params.get('disksymbol', 'sdb')
        xmlstr = xmlstr.replace('SDX', disksymbol)
        xmlstr = xmlstr.replace('device="cdrom" type="block">', 'device="cdrom" type="file">')

    xmlstr = xmlstr.replace('GRAPHIC', graphic)
    logger.info('the graphic type of VM is %s' % graphic)

    if video == "qxl":
        video_model = "<model type='qxl' ram='65536' vram='65536' vgamem='16384' heads='1' primary='yes'/>"
        xmlstr = xmlstr.replace("<model type='cirrus' vram='16384' heads='1'/>", video_model)

    logger.info('the video type of VM is %s' % video)

    logger.info("get system environment information")
    envfile = os.path.join(HOME_PATH, 'global.cfg')
    logger.info("the environment file is %s" % envfile)

    os_arch = guestos + "_" + guestarch
    rhelnewest = params.get('rhelnewest')
    rhelalt = params.get('rhelalt')

    envparser = env_parser.Envparser(envfile)
    if rhelnewest is not None:
        ostree = rhelnewest + "%s/os" % guestarch
        version = re.search(r'RHEL.*?/', rhelnewest).group()[:-1]
        num = version.split("-")[1].split('.')[0]
        kscfg = envparser.get_value("guest", "rhel" + num + "_newest_" + guestarch + "_http_ks")
    elif rhelalt is not None:
        ostree = rhelalt + "%s/os" % guestarch
        version = re.search(r'RHEL-ALT.*?/', rhelalt).group()[:-1]
        num = version.split("-")[2].split('.')[0]
        kscfg = envparser.get_value("guest", "rhel_alt" + num + "_newest_" + guestarch + "_http_ks")
    else:
        ostree = envparser.get_value("guest", os_arch)
        kscfg = envparser.get_value("guest", os_arch + "_http_ks")

    logger.debug('install source:\n    %s' % ostree)
    logger.debug('kisckstart file:\n    %s' % kscfg)

    if ostree == 'http://':
        logger.error("no os tree defined in %s for %s" % (envfile, os_arch))
        return 1

    logger.info('prepare installation...')
    cache_folder = envparser.get_value("variables", "domain_cache_folder")

    if rhelnewest is not None:
        if 'rhel7' in guestos and 'ppc64le' in guestarch:
            bootaddr = envparser.get_value("guest", 'rhel7_newest_ppc64le_bootiso')
        if 'rhel7' in guestos and 'ppc64' in guestarch:
            bootaddr = envparser.get_value("guest", 'rhel7_newest_ppc64_bootiso')
        if 'rhel6' in guestos and 'ppc64':
            bootaddr = envparser.get_value("guest", 'rhel6_newest_ppc64_bootiso')
    if rhelalt is not None:
        bootaddr = envparser.get_value("guest", 'rhel_alt7_newest_ppc64le_bootiso')

    logger.info("begin to customize the custom.iso file")
    bootcd = os.path.join(cache_folder, guestname + "_folder")

    custom_iso = 'custom.iso'
    try:
        if (rhelnewest or rhelalt) is None:
            prepare_cdrom(ostree, kscfg, guestname, guestos, cache_folder, logger)
        else:
            cmd = ('wget -N %s -P %s' % (bootaddr, bootcd))
            custom_iso = bootaddr.split('/')[-1]
            ret = process.run(cmd, shell=True, ignore_status=True)
    except TestError, err:
        logger.error("Failed to prepare boot cdrom!")
        return 1

    xmlstr = xmlstr.replace('CUSTOMISO', bootcd + '/' + custom_iso)
    logger.debug('dump installation guest xml:\n%s' % xmlstr)

    if installtype == 'define':
        logger.info('define guest from xml description')
        try:
            domobj = conn.defineXML(xmlstr)
        except libvirtError as e:
            logger.error("API error message: %s, error code is %s"
                         % (e.get_error_message(), e.get_error_code()))
            logger.error("fail to define domain %s" % guestname)
            return 1

        logger.info('start installation guest ...')

        try:
            domobj.create()
        except libvirtError as e:
            logger.error("API error message: %s, error code is %s"
                         % (e.get_error_message(), e.get_error_code()))
            logger.error("fail to start domain %s" % guestname)
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

    interval = 0
    while interval < 2400:
        time.sleep(10)
        if installtype == 'define':
            state = domobj.info()[0]
            if state == libvirt.VIR_DOMAIN_SHUTOFF:
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

    if interval == 2400:
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

    diskpath = params.get('diskpath', '/var/lib/libvirt/images/libvirt-test-api')
    conn = libvirt.open()
    domain_common.guest_clean(conn, guestname, logger)
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
