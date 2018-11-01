#!/usr/bin/env python
# Install a Windows domain

import os
import re
import time
import shutil
import tempfile

from src import sharedmod
from utils import utils, process
from repos.installation import install_common
from utils.utils import version_compare

#virtio win disk driver
VIRTIO_WIN_64 = "/usr/share/virtio-win/virtio-win_amd64.vfd"
VIRTIO_WIN_32 = "/usr/share/virtio-win/virtio-win_x86.vfd"
VIRTIO_WIN_SERVERS_64 = "/usr/share/virtio-win/virtio-win_servers_amd64.vfd"
VIRTIO_WIN_SERVERS_32 = "/usr/share/virtio-win/virtio-win_servers_x86.vfd"
VIRTIO_WIN10_64 = "/usr/share/virtio-win/virtio-win_w10_amd64.vfd"
VIRTIO_WIN10_32 = "/usr/share/virtio-win/virtio-win_w10_x86.vfd"
#virtio win net driver
VIRTIO_WIN_ISO = "/usr/share/virtio-win/virtio-win.iso"

WIN_UNATTENDED_IMG = "/tmp/win_unattended.img"
HOME_PATH = os.getcwd()

required_params = ('guestname', 'guestos', 'guestarch',)
optional_params = {'memory': 2097152,
                   'vcpu': 1,
                   'disksize': 20,
                   'diskpath': '/var/lib/libvirt/images/libvirt-test-api',
                   'imageformat': 'qcow2',
                   'hddriver': 'virtio',
                   'nicdriver': 'virtio',
                   'macaddr': '52:54:00:97:e4:28',
                   'type': 'define',
                   'uuid': '05867c1a-afeb-300e-e55e-2673391ae080',
                   'xml': 'xmls/install_windows.xml',
                   'guestmachine': 'pc',
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


def prepare_win_unattended(guestname, guestos, guestarch, envparser, logger):
    if "win7" in guestos or "win2008" in guestos:
        cdkey = envparser.get_value("guest", "%s_%s_key" % (guestos, guestarch))
    else:
        cdkey = ""

    windows_unattended_path = os.path.join(HOME_PATH,
                                           "repos/installation/windows_unattended")

    if os.path.exists(WIN_UNATTENDED_IMG):
        os.remove(WIN_UNATTENDED_IMG)

    cmd = 'dd if=/dev/zero of=%s bs=1440k count=1' % WIN_UNATTENDED_IMG
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("failed to create windows unattended image.")
        return 1

    cmd = 'mkfs.msdos -s 1 %s' % WIN_UNATTENDED_IMG
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("failed to format windows unattended image")
        return 1

    unattended_mount = "/tmp/test_api_windows_unattended"
    if os.path.exists(unattended_mount):
        logger.info("the windows unattended mount point folder exists, remove it")
        shutil.rmtree(unattended_mount)

    logger.info("create mount point %s" % unattended_mount)
    os.makedirs(unattended_mount)

    try:
        mount_cmd = 'mount -o loop %s %s' % (WIN_UNATTENDED_IMG, unattended_mount)
        ret = process.run(mount_cmd, shell=True, ignore_status=True)
        if ret.exit_status:
            logger.error(
                "failed to mount %s to %s" % (WIN_UNATTENDED_IMG, unattended_mount))
            return 1

        win_os = ['win2008', 'win7', 'vista', 'win8', 'win2012', 'win10', 'win2016', 'win2019']
        if any(os in guestos for os in win_os):
            dest_fname = "autounattend.xml"
            if guestos == 'win7' and utils.isRelease("8", logger):
                source = os.path.join(windows_unattended_path, "%s_%s_rhel8.xml" % (guestos, guestarch))
            else:
                source = os.path.join(windows_unattended_path, "%s_%s.xml" %
                                      (guestos, guestarch))
        elif '2003' in guestos or 'xp' in guestos:
            dest_fname = "winnt.sif"
            setup_file = 'winnt.bat'
            setup_file_path = os.path.join(windows_unattended_path, setup_file)
            setup_file_dest = os.path.join(unattended_mount, setup_file)
            shutil.copyfile(setup_file_path, setup_file_dest)
            source = os.path.join(windows_unattended_path, "%s_%s.sif" %
                                  (guestos, guestarch))

        dest = os.path.join(unattended_mount, dest_fname)

        unattended_contents = open(source).read()
        dummy_cdkey_re = r'\bLIBVIRT_TEST_CDKEY\b'
        if re.search(dummy_cdkey_re, unattended_contents):
            unattended_contents = re.sub(dummy_cdkey_re, cdkey,
                                         unattended_contents)

        logger.debug("Unattended install %s contents:" % dest_fname)

        win_arch = ""
        if guestarch == "x86_64":
            win_arch = "amd64"
        else:
            if utils.isRelease("8", logger):
                win_arch = "x86"
            else:
                win_arch = "i386"

        driverpath = ""
        drivernet = ""
        win_list = {"win7": "w7",
                    "win8": "w8",
                    "win8u1": "w8.1",
                    "win10": "w10",
                    "win2008": "2k8",
                    "win2008R2": "2k8R2",
                    "win2003": "2k3",
                    "win2012": "2k12",
                    "win2012R2": "2k12R2",
                    "win2016": "2k16"}
        if utils.isRelease("8", logger):
            driverpath = "E:\\viostor\\" + win_list[guestos] + "\\" + win_arch
            drivernet = "E:\\NetKVM\\" + win_list[guestos] + "\\" + win_arch
        else:
            drivernet = "A:\\"
            if guestos == "win8u1":
                driverpath = "A:\\" + win_arch + "\Win8.1"
            else:
                driverpath = "A:\\" + win_arch + "\\" + guestos[0].upper() + guestos[1:]

        unattended_contents = unattended_contents.replace('PATHOFDRIVER', driverpath)
        unattended_contents = unattended_contents.replace('DRIVERNET', drivernet)
        open(dest, 'w').write(unattended_contents)
        logger.debug(unattended_contents)

    finally:
        cmd = "mount | grep %s" % unattended_mount
        ret = process.run(cmd, shell=True, ignore_status=True)
        if ret.exit_status == 0:
            cmd = 'umount %s' % unattended_mount
            ret = process.run(cmd, shell=True, ignore_status=True)
            if ret.exit_status:
                logger.error("umount failed: %s" % cmd)
                return 1

        cleanup(unattended_mount)

    os.chmod(WIN_UNATTENDED_IMG, 0o755)
    logger.info("Boot windows unattended created successfuly")

    return 0


def set_win_driver(xmlstr, guestos, guestarch, logger):
    if utils.isRelease("8", logger):
        xmlstr = xmlstr.replace("DRIVERPATH", VIRTIO_WIN_ISO)
        return xmlstr

    if version_compare("virtio-win", 1, 9, 6, logger):
        win_list = ["win7", "win8", "win8u1", "win10"]
        win_servers_list = ["win2003", "win2008", "win2008R2", "win2012", "win2012R2", "win2016"]
        if guestarch == "x86_64":
            if guestos in win_list:
                xmlstr = xmlstr.replace("DRIVERPATH", VIRTIO_WIN_64)
            elif guestos in win_servers_list:
                xmlstr = xmlstr.replace("DRIVERPATH", VIRTIO_WIN_SERVERS_64)
            else:
                logger.error("%s don't in windows list." % guestos)
        else:
            if guestos in win_list:
                xmlstr = xmlstr.replace("DRIVERPATH", VIRTIO_WIN_32)
            elif guestos in win_servers_list:
                xmlstr = xmlstr.replace("DRIVERPATH", VIRTIO_WIN_SERVERS_32)
            else:
                logger.error("%s don't in windows list." % guestos)
    elif version_compare("virtio-win", 1, 9, 4, logger):
        if guestarch == "x86_64":
            if guestos == "win10":
                xmlstr = xmlstr.replace("DRIVERPATH", VIRTIO_WIN10_64)
            else:
                xmlstr = xmlstr.replace("DRIVERPATH", VIRTIO_WIN_64)
        else:
            if guestos == "win10":
                xmlstr = xmlstr.replace("DRIVERPATH", VIRTIO_WIN10_32)
            else:
                xmlstr = xmlstr.replace("DRIVERPATH", VIRTIO_WIN_32)
    elif version_compare("virtio-win", 1, 9, 3, logger):
        if guestarch == "x86_64":
            xmlstr = xmlstr.replace("DRIVERPATH", VIRTIO_WIN_64)
        else:
            xmlstr = xmlstr.replace("DRIVERPATH", VIRTIO_WIN_32)
    return xmlstr


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

    options = [guestname, guestos, guestarch, nicdriver, hddriver, imageformat, graphic, video, diskpath, seeksize, storage]
    install_common.prepare_env(options, logger)

    if utils.isRelease("8", logger) and guestos == "win2008":
        logger.info("virtio-win don't support win2008 on RHEL 8.")
        return 0

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
    elif hddriver == 'ide':
        xmlstr = xmlstr.replace('DEV', 'hda')
    elif hddriver == 'scsi':
        xmlstr = xmlstr.replace('DEV', 'sda')
    elif hddriver == 'sata':
        xmlstr = xmlstr.replace('DEV', 'sda')
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
    xmlstr = set_win_driver(xmlstr, guestos, guestarch, logger)

    logger.info("get system environment information")
    envparser = install_common.get_env_parser()
    iso_url = envparser.get_value("guest", guestos + '_' + guestarch)
    iso_file = install_common.get_path_from_url(iso_url, ".iso")
    logger.debug('install source: %s' % iso_file)

    logger.info('prepare pre-installation environment...')
    iso_local_path = prepare_iso(iso_file)
    xmlstr = xmlstr.replace('WINDOWSISO', iso_local_path)

    status = prepare_win_unattended(guestname, guestos, guestarch, envparser, logger)
    if status:
        logger.error("making windows unattended image failed")
        return 1
    xmlstr = xmlstr.replace('WIN_UNATTENDED', WIN_UNATTENDED_IMG)

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

    envparser = install_common.get_env_parser()
    iso_url = envparser.get_value("guest", guestos + '_' + guestarch)
    iso_file = install_common.get_path_from_url(iso_url, ".iso")
    iso_local_path = prepare_iso(iso_file)
    if os.path.exists(iso_local_path):
        os.remove(iso_local_path)

    iso_local_path_1 = iso_local_path + ".1"
    if os.path.exists(iso_local_path_1):
        os.remove(iso_local_path_1)

    if os.path.exists(WIN_UNATTENDED_IMG):
        os.remove(WIN_UNATTENDED_IMG)
