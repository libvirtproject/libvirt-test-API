#!/usr/bin/env python
# Install a linux domain from CDROM

import os
import time
import shutil
import tempfile

from src import sharedmod
from utils import utils, process
from repos.installation import install_common
from six.moves import urllib

required_params = ('guestname', 'guestos', 'guestarch')
optional_params = {
                   'memory': 4194304,
                   'vcpu': 2,
                   'disksize': 14,
                   'imageformat': 'qcow2',
                   'qcow2version': 'v3',
                   'hddriver': 'virtio',
                   'nicdriver': 'virtio',
                   'type': 'define',
                   'xml': 'xmls/kvm_linux_guest_install_iso.xml',
                   'guestmachine': 'pc',
                   'graphic': 'spice',
                   'video': 'qxl',
                   'diskpath': '/var/lib/libvirt/images/libvirt-test-api',
                   'disksymbol': 'sdb',
                   'rhelnewest': '',
                   'storage': 'local',
                   'sourcehost': '',
                   'sourcepath': '',
                   'gluster_server_ip': None
}


BOOT_DIR = "/var/lib/libvirt/boot"
VMLINUZ = os.path.join(BOOT_DIR, 'vmlinuz')
INITRD = os.path.join(BOOT_DIR, 'initrd.img')


def prepare_iso(isolink, cache_floder, nfs_server, logger):
    """ Download iso file from isolink to cache_floder
        file into it for automatic guest installation
    """
    cmd = "wget " + isolink + " -P " + cache_floder
    ret, out = utils.exec_cmd(cmd, shell=True)
    if ret:
        iso_name = os.path.basename(isolink)
        url = "http://" + nfs_server + "/test-api-iso/" + iso_name
        logger.info("Download iso failed. ISO link: %s, out: %s" % (isolink, out))
        logger.info("Try to get iso from server. %s" % url)
        cmd = "wget " + url + " -P " + cache_floder
        ret, out = utils.exec_cmd(cmd, shell=True)
        if ret:
            logger.error("Download iso failed. Out: %s" % out)


def set_xml(sourcehost, sourcepath, xmlstr, hddriver, diskpath, ks, nfs_server, logger):
    boot_driver = install_common.get_boot_driver(hddriver, logger)
    xmlstr = install_common.set_disk_xml(hddriver, xmlstr, diskpath,
                                         logger, sourcehost, sourcepath)
    ks_name = os.path.basename(ks)
    tmppath = tempfile.mkdtemp()
    cmd = "mount -t nfs %s:/srv/www/html/test-api-ks/tmp-ks %s" % (nfs_server, tmppath)
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("mount failed: %s" % cmd)
        return 1
    if os.path.exists("%s/%s" % (tmppath, ks_name)):
        os.remove("%s/%s" % (tmppath, ks_name))

    urllib.request.urlretrieve(ks, "%s/%s" % (tmppath, ks_name))
    old_ks_fp = open('%s/%s' % (tmppath, ks_name), "r+")
    new_ks_fp = open("%s/test_api_iso_ks.cfg" % tmppath, "w")
    old_ks_file = old_ks_fp.read()
    old_ks_file = old_ks_file.replace("--boot-drive=", "--boot-drive=%s" % boot_driver)
    new_ks_fp.write(old_ks_file)
    new_ks_fp.close()
    old_ks_fp.close()
    shutil.move("%s/test_api_iso_ks.cfg" % tmppath, "%s/%s" % (tmppath, ks_name))
    cmd = "umount %s" % tmppath
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("umount failed: %s" % cmd)
        return 1
    xmlstr = xmlstr.replace('KS', 'http://%s/test-api-ks/tmp-ks/%s' % (nfs_server, ks_name))
    shutil.rmtree(tmppath)

    return xmlstr


def install_linux_iso(params):
    """ install a new virtual machine """
    logger = params['logger']

    guestname = params.get('guestname')
    guestos = params.get('guestos')
    guestarch = params.get('guestarch')
    bridge = params.get('bridgename', 'virbr0')
    xmlstr = params['xml']
    seeksize = params.get('disksize', 14)
    nicdriver = params.get('nicdriver', 'virtio')
    hddriver = params.get('hddriver', 'virtio')
    diskpath = params.get('diskpath', '/var/lib/libvirt/images/libvirt-test-api')
    imageformat = params.get('imageformat', 'qcow2')
    graphic = params.get('graphic', 'spice')
    video = params.get('video', 'qxl')
    installtype = params.get('type', 'define')
    rhelnewest = params.get('rhelnewest')
    storage = params.get('storage', 'local')
    sourcehost = params.get('sourcehost', '')
    sourcepath = params.get('sourcepath', '')

    options = [guestname, guestos, guestarch, nicdriver, hddriver,
               imageformat, graphic, video, diskpath, seeksize, storage]
    install_common.prepare_env(options, logger)

    logger.info("rhelnewest: %s" % rhelnewest)
    mountpath = tempfile.mkdtemp()
    diskpath = install_common.setup_storage(params, mountpath, logger)
    xmlstr = xmlstr.replace('/var/lib/libvirt/images/libvirt-test-api', diskpath)

    xmlstr = xmlstr.replace('GRAPHIC', graphic)
    xmlstr = install_common.set_disk_xml(hddriver, xmlstr, diskpath, logger, sourcehost, sourcepath)
    xmlstr = install_common.set_video_xml(video, xmlstr)
    ostree = install_common.get_ostree(rhelnewest, guestos, guestarch, logger)
    kscfg = install_common.get_kscfg(rhelnewest, guestos, guestarch, "iso", logger)
    isolink = install_common.get_iso_link(rhelnewest, guestos, guestarch, logger)

    nfs_server = install_common.get_value_from_global("other", "nfs_server")
    sourcehost = params.get('sourcehost', '')
    sourcepath = params.get('sourcepath', '')
    xmlstr = set_xml(sourcehost, sourcepath, xmlstr, hddriver, diskpath, kscfg, nfs_server, logger)

    logger.info("begin to download the iso file")
    cache_floder = "/var/lib/libvirt/images/"
    bootcd = cache_floder + isolink.split("/")[-1]
    if not os.path.exists(bootcd):
        prepare_iso(isolink, cache_floder, nfs_server, logger)
        logger.info("Finish download the iso file: %s" % bootcd)

    macaddr = utils.get_rand_mac()
    xmlstr = xmlstr.replace('MACADDR', macaddr)

    xmlstr = xmlstr.replace('CUSTOMISO', bootcd)
    xmlstr = xmlstr.replace('KS', kscfg)
    xmlstr = install_common.get_vmlinuz_initrd(ostree, xmlstr, logger)
    logger.debug('dump installation guest xml:\n%s' % xmlstr)

    conn = sharedmod.libvirtobj['conn']
    if not install_common.start_guest(conn, installtype, xmlstr, logger):
        logger.error("fail to define domain %s" % guestname)
        return 1

    if not install_common.wait_install(conn, guestname, xmlstr, installtype, "iso", logger):
        return 1

    time.sleep(60)
    if storage != "local":
        install_common.clean_guest(guestname, logger)
        install_common.cleanup_storage(params, mountpath, logger)

    return 0


def install_linux_iso_clean(params):
    """ clean testing environment """
    logger = params['logger']
    guestname = params.get('guestname')
    guestos = params.get('guestos')
    guestarch = params.get('guestarch')

    os_arch = guestos + "_" + guestarch
    local_url = install_common.get_value_from_global("other", "local_url")
    remote_url = install_common.get_value_from_global("other", "remote_url")
    location = utils.get_local_hostname()
    rhelnewest = params.get('rhelnewest')
    if rhelnewest is not None:
        if local_url in rhelnewest:
            repo_name = rhelnewest.split('/')[6]
        elif remote_url in rhelnewest:
            repo_name = rhelnewest.split('/')[4]
        isopath = ("/var/lib/libvirt/images/%s-Server-%s-dvd1.iso" %
                   (repo_name, guestarch))
    else:
        os_arch = guestos + "_" + guestarch
        isolink = install_common.get_value_from_global("guest", os_arch + "_iso")
        isopath = '/var/lib/libvirt/images/' + isolink.split('/')[-1]

    if os.path.exists(isopath):
        os.remove(isopath)

    diskpath = params.get('diskpath', "/var/lib/libvirt/images/libvirt-test-api")
    install_common.clean_guest(guestname, logger)
    install_common.remove_all(diskpath, logger)
    install_common.remove_vmlinuz_initrd(logger)
