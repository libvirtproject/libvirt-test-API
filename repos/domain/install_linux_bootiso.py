#!/usr/bin/env python
# Install a linux domain from CDROM
# The iso file may be locked by other proces, and cause the failure of installation
import os
import re
import time
import shutil

from src.exception import TestError

from src import sharedmod
from utils import process
from repos.domain import install_common
from six.moves import urllib


required_params = ('guestname', 'guestos', 'guestarch',)
optional_params = {
                   'memory': 2097152,
                   'vcpu': 1,
                   'disksize': 10,
                   'diskpath': '/var/lib/libvirt/images/libvirt-test-api',
                   'imageformat': 'qcow2',
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


def mk_kickstart_iso(kscfg, guestos, logger):
    cwd = os.getcwd()
    boot_iso = "boot.iso"
    custom_iso = "custom.iso"
    boot_iso_dir = "/mnt/boot_iso_dir"
    custom_iso_dir = "/mnt/new"
    kernel_args = os.getenv('kernel_args', '')

    logger.debug("clean up in case of previous failure")
    install_common.remove_all(boot_iso_dir, logger)
    install_common.remove_all(custom_iso_dir, logger)

    logger.debug("create work directories")
    os.makedirs(boot_iso_dir)

    logger.debug("mount " + boot_iso)
    ret = process.run("mount -t iso9660 -o loop %s %s"
                      % (boot_iso, boot_iso_dir), shell=True, ignore_status=True)
    if ret.exit_status != 0:
        raise RuntimeError('Failed to start making custom iso: ' + ret.stdout)

    logger.debug("copy original iso files to custom work directory")
    shutil.copytree(boot_iso_dir, custom_iso_dir)

    for root, dirs, files in os.walk(custom_iso):
        for i in dirs:
            os.chmod(os.path.join(root, i), 511)  # DEC 511 == OCT 777
        for i in files:
            os.chmod(os.path.join(root, i), 511)

    ret = process.run("umount %s" % boot_iso_dir, shell=True, ignore_status=True)
    if ret.exit_status != 0:
        raise RuntimeError('Failed umounting boot iso: ' + ret.stdout)

    ret = process.run("isoinfo -d -i %s |grep 'Volume id:'" % boot_iso, shell=True, ignore_status=True)
    logger.debug("ret.stdout :" + ret.stdout)

    logger.debug("editing config files")
    new_cfg_filename = 'tmp_cfg'
    new_cfg = open('tmp_cfg', 'w')

    if "ppc" in ret.stdout:
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
                        % (ret.stdout, kscfg))
            new_cfg.write(line)

        new_cfg.close()
        old_cfg.close()

        install_common.remove_all(old_cfg_filename, logger)
        shutil.move(new_cfg_filename, old_cfg_filename)
        os.chdir(custom_iso_dir)
        mkisofs_command = ('mkisofs -R -V "%s" -sysid PPC -chrp-boot '
                           '-U -prep-boot ppc/chrp/yaboot -hfs-bless ppc/mac -no-desktop '
                           '-allow-multidot -volset 4 -volset-size 1 -volset-seqno 1 '
                           '-hfs-volid 4 -o %s/%s .' % (ret.stdout, cwd, custom_iso))
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
        install_common.remove_all(kscfg, logger)

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

        install_common.remove_all(old_cfg_filename, logger)
        shutil.move(new_cfg_filename, old_cfg_filename)
        os.chdir(custom_iso_dir)
        mkisofs_command = ('mkisofs -R -b '
                           'isolinux/isolinux.bin -no-emul-boot '
                           '-boot-load-size 4 -boot-info-table -o %s/%s .'
                           % (cwd, custom_iso))

    ret = process.run(mkisofs_command, shell=True, ignore_status=True)
    if ret.exit_status != 0:
        raise RuntimeError("Failed to make custom_iso, error %d: %s!" % (ret, ret.stdout))

    # clean up
    install_common.remove_all(boot_iso_dir, logger)
    install_common.remove_all(custom_iso_dir, logger)


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

    urllib.request.urlretrieve(boot_path, '%s/boot.iso' % new_dir)
    time.sleep(10)

    urllib.request.urlretrieve(kscfg, '%s/%s' % (new_dir, ks_name))
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


def install_linux_bootiso(params):
    """ install a new virtual machine """
    logger = params['logger']

    guestname = params.get('guestname')
    guestos = params.get('guestos')
    guestarch = params.get('guestarch')
    bridge = params.get('bridgename', 'virbr0')
    xmlstr = params['xml']
    seeksize = params.get('disksize', 10)
    nicdriver = params.get('nicdriver', 'virtio')
    hddriver = params.get('hddriver', 'virtio')
    diskpath = params.get('diskpath', '/var/lib/libvirt/images/libvirt-test-api')
    imageformat = params.get('imageformat', 'qcow2')
    graphic = params.get('graphic', 'spice')
    video = params.get('video', 'qxl')
    installtype = params.get('type', 'define')
    rhelnewest = params.get('rhelnewest')

    options = [guestname, guestos, guestarch, nicdriver, hddriver,
               imageformat, graphic, video, diskpath, seeksize, "local"]
    install_common.prepare_env(options, logger)

    install_common.remove_all(diskpath, logger)
    install_common.create_image(diskpath, seeksize, imageformat, logger)

    logger.info("rhelnewest: %s" % rhelnewest)
    xmlstr = xmlstr.replace('GRAPHIC', graphic)
    xmlstr = install_common.set_disk_xml(hddriver, xmlstr, diskpath, logger)
    xmlstr = install_common.set_video_xml(video, xmlstr)
    ostree = install_common.get_ostree(rhelnewest, guestos, guestarch, logger)
    kscfg = install_common.get_kscfg(rhelnewest, guestos, guestarch, "http", logger)
    cache_folder = install_common.get_value_from_global("variables", "domain_cache_folder")

    try:
        logger.info("begin to customize the custom.iso file")
        prepare_cdrom(ostree, kscfg, guestname, guestos, cache_folder, logger)
    except TestError as err:
        logger.error("Failed to prepare boot cdrom!")
        return 1

    bootcd = ('%s/custom.iso'
              % (os.path.join(cache_folder, guestname + "_folder")))
    xmlstr = xmlstr.replace('CUSTOMISO', bootcd)
    logger.debug('dump installation guest xml:\n%s' % xmlstr)

    conn = sharedmod.libvirtobj['conn']
    if not install_common.start_guest(conn, installtype, xmlstr, logger):
        logger.error("fail to define domain %s" % guestname)
        return 1

    if not install_common.wait_install(conn, guestname, xmlstr, installtype, "bootiso", logger):
        return 1

    if not install_common.check_guest_ip(guestname, logger):
        return 1

    time.sleep(60)

    return 0


def install_linux_bootiso_clean(params):
    """ clean testing environment """
    logger = params['logger']
    guestname = params.get('guestname')
    diskpath = params.get('diskpath', '/var/lib/libvirt/images/libvirt-test-api')

    install_common.clean_guest(guestname, logger)
    install_common.remove_all(diskpath, logger)

    cache_folder = install_common.get_value_from_global("variables", "domain_cache_folder")
    install_common.remove_all(cache_folder + '/' + guestname + "_folder", logger)
