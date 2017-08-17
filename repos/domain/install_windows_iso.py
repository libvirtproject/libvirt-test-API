#!/usr/bin/env python
# Install a Windows domain

import os
import sys
import re
import time
import commands
import shutil
import urllib
import requests
import tempfile

import libvirt
from libvirt import libvirtError

from src import sharedmod
from src import env_parser
from utils import utils
from repos.domain import install_common


VIRSH_QUIET_LIST = "virsh --quiet list --all|awk '{print $2}'|grep \"^%s$\""
VM_STAT = "virsh --quiet list --all| grep \"\\b%s\\b\"|grep off"
VM_DESTROY = "virsh destroy %s"
VM_UNDEFINE = "virsh undefine %s"

#virtio win disk driver
VIRTIO_WIN_64 = "/usr/share/virtio-win/virtio-win_amd64.vfd"
VIRTIO_WIN_32 = "/usr/share/virtio-win/virtio-win_x86.vfd"
#virtio win net driver
#VIRTIO_WIN_ISO = "/usr/share/virtio-win/virtio-win.iso"

FLOOPY_IMG = "/tmp/floppy.img"
HOME_PATH = os.getcwd()

required_params = ('guestname', 'guestos', 'guestarch',)
optional_params = {'memory': 1048576,
                   'vcpu': 1,
                   'disksize': 20,
                   'diskpath': '/var/lib/libvirt/images/libvirt-test-api',
                   'imageformat': 'qcow2',
                   'hddriver': 'virtio',
                   'nicdriver': 'virtio',
                   'macaddr': '52:54:00:97:e4:28',
                   'type': 'define',
                   'uuid': '05867c1a-afeb-300e-e55e-2673391ae080',
                   'xml': 'xmls/kvm_windows_guest_install_cdrom.xml',
                   'guestmachine': 'pc',
                   'driverpath': '/usr/share/virtio-win/virtio-win_amd64.vfd',
                   'graphic': 'spice',
                   'video': 'qxl',
                   'storage': 'local',
                   'sourcehost': '',
                   'sourcepath': '',
                   }


def cleanup(mount):
    """Clean up a previously used mountpoint.
       @param mount: Mountpoint to be cleaned up.
    """
    if os.path.isdir(mount):
        if os.path.ismount(mount):
            logger.error("Path %s is still mounted, please verify" % mount)
        else:
            logger.info("Removing mount point %s" % mount)
            os.rmdir(mount)


def prepare_iso(iso_file):
    """fetch windows iso file
    """
    # download iso_file into /tmp
    windows_iso = iso_file.split('/')[-1]
    iso_local_path = os.path.join("/tmp", windows_iso)
    if not os.path.exists(iso_local_path):
        cmd = "wget " + iso_file + " -P " + "/tmp"
        utils.exec_cmd(cmd, shell=True)
    return iso_local_path


def prepare_floppy_image(guestname, guestos, guestarch,
                         windows_unattended_path, cdkey, FLOOPY_IMG):
    """Making corresponding floppy images for the given guestname
    """
    if os.path.exists(FLOOPY_IMG):
        os.remove(FLOOPY_IMG)

    create_cmd = 'dd if=/dev/zero of=%s bs=1440k count=1' % FLOOPY_IMG
    (status, text) = commands.getstatusoutput(create_cmd)
    if status:
        logger.error("failed to create floppy image")
        return 1

    format_cmd = 'mkfs.msdos -s 1 %s' % FLOOPY_IMG
    (status, text) = commands.getstatusoutput(format_cmd)
    if status:
        logger.error("failed to format floppy image")
        return 1

    floppy_mount = "/mnt/libvirt_floppy"
    if os.path.exists(floppy_mount):
        logger.info("the floppy mount point folder exists, remove it")
        shutil.rmtree(floppy_mount)

    logger.info("create mount point %s" % floppy_mount)
    os.makedirs(floppy_mount)

    try:
        mount_cmd = 'mount -o loop %s %s' % (FLOOPY_IMG, floppy_mount)
        (status, text) = commands.getstatusoutput(mount_cmd)
        if status:
            logger.error(
                "failed to mount /tmp/floppy.img to /mnt/libvirt_floppy")
            return 1

        win_os = ['win2008', 'win7', 'vista', 'win8', 'win2012', 'win10', 'win2016']
        if any(os in guestos for os in win_os):
            dest_fname = "autounattend.xml"
            source = os.path.join(windows_unattended_path, "%s_%s.xml" %
                                  (guestos, guestarch))

        elif '2003' in guestos or 'xp' in guestos:
            dest_fname = "winnt.sif"
            setup_file = 'winnt.bat'
            setup_file_path = os.path.join(windows_unattended_path, setup_file)
            setup_file_dest = os.path.join(floppy_mount, setup_file)
            shutil.copyfile(setup_file_path, setup_file_dest)
            source = os.path.join(windows_unattended_path, "%s_%s.sif" %
                                  (guestos, guestarch))

        dest = os.path.join(floppy_mount, dest_fname)

        unattended_contents = open(source).read()
        dummy_cdkey_re = r'\bLIBVIRT_TEST_CDKEY\b'
        if re.search(dummy_cdkey_re, unattended_contents):
            unattended_contents = re.sub(dummy_cdkey_re, cdkey,
                                         unattended_contents)

        logger.debug("Unattended install %s contents:" % dest_fname)

        if guestos == "win8u1":
            driverpath = "Win8.1"
        else:
            driverpath = guestos[0].upper() + guestos[1:]

        unattended_contents = unattended_contents.replace('PATHOFDRIVER', driverpath)
        open(dest, 'w').write(unattended_contents)
        logger.debug(unattended_contents)

    finally:
        cmd = "mount | grep '/mnt/libvirt_floppy'"
        (stat, out) = commands.getstatusoutput(cmd)
        if stat == 0:
            umount_cmd = 'umount %s' % floppy_mount
            (stat, out) = commands.getstatusoutput(umount_cmd)
            if stat:
                logger.error("umount failed: %s" % umount_cmd)
                return 1

        cleanup(floppy_mount)

    os.chmod(FLOOPY_IMG, 0o755)
    logger.info("Boot floppy created successfuly")

    return 0


def install_windows_iso(params):
    """ install a windows guest virtual machine by using iso file """
    # Initiate and check parameters
    global logger

    logger = params['logger']
    guestname = params.get('guestname')
    guestos = params.get('guestos')
    guestarch = params.get('guestarch')
    seeksize = params.get('disksize', 20)
    imageformat = params.get('imageformat', 'qcow2')
    diskpath = params.get('diskpath', '/var/lib/libvirt/images/libvirt-test-api')
    nicdriver = params.get('nicdriver', 'virtio')
    graphic = params.get('graphic', 'spice')
    video = params.get('video', 'qxl')
    xmlstr = params.get('xml')
    uuid = params.get('uuid', '05867c1a-afeb-300e-e55e-2673391ae080')
    hddriver = params.get('hddriver', 'virtio')
    sourcehost = params.get('sourcehost', '')
    sourcepath = params.get('sourcepath', '')
    storage = params.get('storage', 'local')
    installtype = params.get('type', 'define')

    options = [guestname, guestos, guestarch, nicdriver, hddriver,
              imageformat, graphic, video, diskpath, seeksize, storage]
    install_common.prepare_env(options, logger)

    mountpath = tempfile.mkdtemp()
    diskpath = install_common.setup_storage(params, mountpath, logger)
    xmlstr = xmlstr.replace('/var/lib/libvirt/images/libvirt-test-api', diskpath)

    xmlstr = install_common.set_video_xml(video, xmlstr)

    if guestos == "win10" or guestos == "win2016":
        xmlstr = xmlstr.replace("</os>\n  <features>", "</os>\n  <cpu mode="
                                "'custom' match='exact'>\n    <model fallback="
                                "'allow'>Westmere</model>\n    <feature "
                                "policy='optional' name='aes'/>\n  </cpu>\n"
                                "  <features>")

    xmlstr = xmlstr.replace('UUID', uuid)

    # NICDRIVER
    if nicdriver == 'virtio' or nicdriver == 'e1000' or nicdriver == 'rtl8139':
        xmlstr = xmlstr.replace("type='virtio'", "type='%s'" % nicdriver)
    else:
        logger.error('the %s is unspported by KVM' % nicdriver)
        return 1

    # Graphic type
    xmlstr = xmlstr.replace('GRAPHIC', graphic)

    # Hard disk type
    if hddriver == 'virtio':
        xmlstr = xmlstr.replace('DEV', 'vda')
        if guestarch == "x86_64":
            xmlstr = xmlstr.replace(VIRTIO_WIN_64, VIRTIO_WIN_64)
        else:
            xmlstr = xmlstr.replace(VIRTIO_WIN_64, VIRTIO_WIN_32)
    elif hddriver == 'ide':
        xmlstr = xmlstr.replace('DEV', 'hda')
    elif hddriver == 'scsi':
        xmlstr = xmlstr.replace('DEV', 'sda')
    elif hddriver == 'sata':
        xmlstr = xmlstr.replace('DEV', 'sda')
        if guestarch == "x86_64":
            xmlstr = xmlstr.replace(VIRTIO_WIN_64, VIRTIO_WIN_64)
        else:
            xmlstr = xmlstr.replace(VIRTIO_WIN_64, VIRTIO_WIN_32)
    elif hddriver == 'lun':
        xmlstr = xmlstr.replace("'lun'", "'virtio'")
        xmlstr = xmlstr.replace('DEV', 'vda')
        xmlstr = xmlstr.replace('device="disk"', 'device="lun"')
        xmlstr = xmlstr.replace('disk device="lun" type="file"', 'disk device="lun" type="block"')
        iscsi_path = install_common.get_iscsi_disk_path(sourcehost, sourcepath)
        xmlstr = xmlstr.replace("file='%s'" % diskpath, "dev='%s'" % iscsi_path)
        xmlstr = xmlstr.replace('device="cdrom" type="block">', 'device="cdrom" type="file">')
    elif hddriver == 'scsilun':
        xmlstr = xmlstr.replace("'scsilun'", "'scsi'")
        xmlstr = xmlstr.replace('DEV', 'sda')
        xmlstr = xmlstr.replace('device="disk"', 'device="lun"')
        xmlstr = xmlstr.replace('disk device="lun" type="file"', 'disk device="lun" type="block"')
        iscsi_path = install_common.get_iscsi_disk_path(sourcehost, sourcepath)
        xmlstr = xmlstr.replace("file='%s'" % diskpath, "dev='%s'" % iscsi_path)
        xmlstr = xmlstr.replace('device="cdrom" type="block">', 'device="cdrom" type="file">')

    logger.info("get system environment information")
    envfile = os.path.join(HOME_PATH, 'global.cfg')
    logger.info("the environment file is %s" % envfile)

    # Get iso file based on guest os and arch from global.cfg
    envparser = env_parser.Envparser(envfile)
    iso_url = envparser.get_value("guest", guestos + '_' + guestarch)
    iso_file = install_common.get_path_from_url(iso_url, ".iso")

    if "win7" in guestos or "win2008" in guestos:
        cdkey = envparser.get_value("guest", "%s_%s_key" % (guestos, guestarch))
    else:
        cdkey = ""

    windows_unattended_path = os.path.join(HOME_PATH,
                                           "repos/domain/windows_unattended")

    logger.debug('install source: %s' % iso_file)
    logger.info('prepare pre-installation environment...')

    iso_local_path = prepare_iso(iso_file)
    xmlstr = xmlstr.replace('WINDOWSISO', iso_local_path)

    status = prepare_floppy_image(guestname, guestos, guestarch,
                                  windows_unattended_path, cdkey, FLOOPY_IMG)
    if status:
        logger.error("making floppy image failed")
        return 1
    xmlstr = xmlstr.replace('FLOPPY', FLOOPY_IMG)

    logger.debug('dump installation guest xml:\n%s' % xmlstr)

    conn = sharedmod.libvirtobj['conn']
    if not install_common.start_guest(conn, installtype, xmlstr, logger):
        logger.error("fail to define domain %s" % guestname)
        return 1

    if not install_common.wait_install(conn, guestname, xmlstr, installtype, "iso", logger, "12000", guestos, iso_file):
        return 1

    if not install_common.check_guest_ip(guestname, logger):
        return 1

    time.sleep(60)
    if storage != "local":
        install_common.clean_guest(guestname, logger)
        install_common.cleanup_storage(params, mountpath, logger)

    return 0


def install_windows_iso_clean(params):
    """ clean testing environment """
    logger = params['logger']
    guestname = params.get('guestname')
    guestos = params.get('guestos')
    guestarch = params.get('guestarch')
    diskpath = params.get('diskpath', '/var/lib/libvirt/images/libvirt-test-api')

    install_common.clean_guest(guestname, logger)
    install_common.remove_all(diskpath, logger)

    envfile = os.path.join(HOME_PATH, 'global.cfg')
    envparser = env_parser.Envparser(envfile)
    iso_url = envparser.get_value("guest", guestos + '_' + guestarch)
    iso_file = install_common.get_path_from_url(iso_url, ".iso")
    iso_local_path = prepare_iso(iso_file)
    if os.path.exists(iso_local_path):
        os.remove(iso_local_path)

    iso_local_path_1 = iso_local_path + ".1"
    if os.path.exists(iso_local_path_1):
        os.remove(iso_local_path_1)

    if os.path.exists(FLOOPY_IMG):
        os.remove(FLOOPY_IMG)
