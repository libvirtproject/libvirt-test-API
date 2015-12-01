#!/usr/bin/env python
# Install a Windows domain

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

VIRSH_QUIET_LIST = "virsh --quiet list --all|awk '{print $2}'|grep \"^%s$\""
VM_STAT = "virsh --quiet list --all| grep \"\\b%s\\b\"|grep off"
VM_DESTROY = "virsh destroy %s"
VM_UNDEFINE = "virsh undefine %s"

FLOOPY_IMG = "/tmp/floppy.img"
HOME_PATH = os.getcwd()

required_params = ('guestname', 'guestos', 'guestarch',)
optional_params = {'memory': 1048576,
                   'vcpu': 1,
                   'disksize': 20,
                   'diskpath': '/var/lib/libvirt/images/libvirt-test-api',
                   'imageformat': 'raw',
                   'hddriver': 'virtio',
                   'nicdriver': 'virtio',
                   'macaddr': '52:54:00:97:e4:28',
                   'type': 'define',
                   'uuid': '05867c1a-afeb-300e-e55e-2673391ae080',
                   'xml': 'xmls/kvm_windows_guest_install_cdrom.xml',
                   'guestmachine': 'pc',
                   'driverpath': '/usr/share/virtio-win/virtio-win_amd64.vfd',
                   'graphic': 'vnc',
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

        if '2008' in guestos or '7' in guestos or 'vista' in guestos \
            or 'win8' in guestos or "win2012" in guestos:
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
        logger.debug(unattended_contents)
        
        driverpath = guestos[0].upper() + guestos[1:]
        unattended_contents = unattended_contents.replace('PATHOFDRIVER',driverpath)
        open(dest, 'w').write(unattended_contents)

    finally:
        umount_cmd = 'umount %s' % floppy_mount
        r = 'check mounting status'
        while r != '':
            (s, r) = commands.getstatusoutput("lsof /mnt/libvirt_floppy|grep mount")
        (status, text) = commands.getstatusoutput(umount_cmd)
        if status:
            logger.error("failed to umount %s" % floppy_mount)
            return 1

        cleanup(floppy_mount)

    os.chmod(FLOOPY_IMG, 0o755)
    logger.info("Boot floppy created successfuly")

    return 0


def prepare_boot_guest(domobj, xmlstr, guestname, installtype):
    """ After guest installation is over, undefine the guest with
        bootting off cdrom, to define the guest to boot off harddisk.
    """
    xmlstr = xmlstr.replace('<boot dev="cdrom"/>', '<boot dev="hd"/>')
    xmlstr = re.sub('<disk device="floppy".*\n.*\n.*\n.*\n.*\n', '', xmlstr)
    xmlstr = re.sub('<disk device="cdrom".*\n.*\n.*\n.*\n.*\n', '', xmlstr)
    xmlstr = re.sub('<disk type="file".*\n.*\n.*\n.*\n.*\n', '', xmlstr)

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


def check_domain_state(conn, guestname):
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


def install_windows_cdrom(params):
    """ install a windows guest virtual machine by using iso file """
    # Initiate and check parameters
    global logger
    logger = params['logger']

    guestname = params.get('guestname')
    guestos = params.get('guestos')
    guestarch = params.get('guestarch')
    xmlstr = params['xml']

    logger.info("the name of guest is %s" % guestname)

    conn = sharedmod.libvirtobj['conn']
    check_domain_state(conn, guestname)

    logger.info("the macaddress is %s" %
                params.get('macaddr', '52:54:00:97:e4:28'))

    diskpath = params.get('diskpath', '/var/lib/libvirt/images/libvirt-test-api')

    logger.info("disk image is %s" % diskpath)
    seeksize = params.get('disksize', 20)
    imageformat = params.get('imageformat', 'raw')
    if  os.path.exists(diskpath):
        os.remove(diskpath)

    logger.info("create disk image with size %sG, format %s" % (seeksize, imageformat))
    disk_create = "qemu-img create -f %s %s %sG" % \
        (imageformat, diskpath, seeksize)
    logger.debug("the command line of creating disk images is '%s'" %
                 disk_create)

    (status, message) = commands.getstatusoutput(disk_create)
    if status != 0:
        logger.debug(message)

    os.chown(diskpath, 107, 107)
    logger.info("creating disk images file is successful.")
    
    # NICDRIVER
    nicdriver = params.get('nicdriver', 'virtio')
    if nicdriver == 'virtio' or nicdriver == 'e1000' or nicdriver == 'rtl8139':
        xmlstr = xmlstr.replace("type='virtio'", "type='%s'" %nicdriver)
    else:
        logger.error('the %s is unspported by KVM' % nicdriver)
        return 1
    logger.info('the nicdriver is %s' % nicdriver)

    # Hard disk type 
    hddriver = params.get('hddriver', 'virtio')
    if hddriver == 'virtio':
        xmlstr = xmlstr.replace('DEV', 'vda')
        driverpath = params.get('driverpath','/usr/share/virtio-win/virtio-win_amd64.vfd')
        xmlstr = xmlstr.replace('/usr/share/virtio-win/virtio-win_amd64.vfd', 
                                 driverpath)
    elif hddriver == 'ide':
        xmlstr = xmlstr.replace('DEV', 'hda')
    elif hddriver == 'scsi':
        xmlstr = xmlstr.replace('DEV', 'sda')
        driverpath = params.get('driverpath','/usr/share/virtio-win/virtio-win_amd64.vfd')
        xmlstr = xmlstr.replace('/usr/share/virtio-win/virtio-win_amd64.vfd', 
                                 driverpath)

    logger.info("get system environment information")
    envfile = os.path.join(HOME_PATH, 'global.cfg')
    logger.info("the environment file is %s" % envfile)
    
    # Graphic type
    graphic = params.get('graphic', 'vnc')
    if graphic != 'vnc' and graphic != 'spice':
        logger.error("the %s is unspported" %graphic)
        return 1
    else:
        xmlstr = xmlstr.replace('vnc', graphic)
    logger.info("the graphic of guests is %s" % graphic)


    # Get iso file based on guest os and arch from global.cfg
    envparser = env_parser.Envparser(envfile)
    iso_file = envparser.get_value("guest", guestos + '_' + guestarch)
    cdkey = envparser.get_value("guest", "%s_%s_key" % (guestos, guestarch))

    windows_unattended_path = os.path.join(HOME_PATH,
                                           "repos/domain/windows_unattended")

    logger.debug('install source:\n    %s' % iso_file)
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
    
    # Generate guest xml
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
            conn.createXML(xmlstr, 0)
        except libvirtError as e:
            logger.error("API error message: %s, error code is %s"
                         % (e.message, e.get_error_code()))
            logger.error("fail to define domain %s" % guestname)
            return 1

    interval = 0
    while(interval < 7200):
        time.sleep(20)
        if installtype == 'define':
            state = domobj.info()[0]
            if(state == libvirt.VIR_DOMAIN_SHUTOFF):
                logger.info("guest installaton of define type is complete.")
                logger.info("boot guest vm off harddisk")
                ret = prepare_boot_guest(
                    domobj, xmlstr, guestname, installtype)
                if ret:
                    logger.info("booting guest vm off harddisk failed")
                    return 1
                break
            else:
                interval += 20
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
                    domobj, xmlstr, guestname, installtype)
                if ret:
                    logger.info("booting guest vm off harddisk failed")
                    return 1
                break
            else:
                interval += 20
                logger.info('%s seconds passed away...' % interval)

    if interval == 7200:
        logger.info("guest installation timeout 7200s")
        return 1
    else:
        logger.info("guest is booting up")

    logger.info("get the mac address of vm %s" % guestname)
    mac = utils.get_dom_mac_addr(guestname)
    logger.info("the mac address of vm %s is %s" % (guestname, mac))

    timeout = 600

    while timeout:
        time.sleep(10)
        timeout -= 10

        ip = utils.mac_to_ip(mac, 0)

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


def install_windows_cdrom_clean(params):
    """ clean testing environment """
    logger = params['logger']
    guestname = params.get('guestname')

    diskpath = params.get('diskpath', '/var/lib/libvirt/images/libvirt-test-api')
    diskpath = diskpath + params['guestname']
    
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

    guestos = params.get('guestos')
    guestarch = params.get('guestarch')

    envfile = os.path.join(HOME_PATH, 'global.cfg')
    envparser = env_parser.Envparser(envfile)
    iso_file = envparser.get_value("guest", guestos + '_' + guestarch)

    iso_local_path = prepare_iso(iso_file)
    if os.path.exists(iso_local_path):
        os.remove(iso_local_path)

    iso_local_path_1 = iso_local_path + ".1"
    if os.path.exists(iso_local_path_1):
        os.remove(iso_local_path_1)

    if os.path.exists(diskpath):
        os.remove(diskpath)

    if os.path.exists(FLOOPY_IMG):
        os.remove(FLOOPY_IMG)
