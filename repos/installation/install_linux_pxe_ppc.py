#!/usr/bin/env python
# Install a linux domain from pxe

import os
import re
import time
import shutil
import libvirt

from six.moves import urllib
from libvirt import libvirtError
from src import sharedmod
from src import env_parser
from utils import utils, process
from repos.domain import domain_common
from repos.installation import install_common

required_params = ('guestname', 'guestos', 'guestarch',)
optional_params = {
                   'memory': 4194304,
                   'vcpu': 2,
                   'disksize': 14,
                   'diskpath': '/var/lib/libvirt/images/libvirt-test-api',
                   'imageformat': 'qcow2',
                   'hddriver': 'virtio',
                   'nicdriver': 'virtio',
                   'macaddr': '52:54:00:97:e4:28',
                   'type': 'define',
                   'xml': 'xmls/install_pxe_ppc.xml',
                   'graphic': "vnc",
                   'video': 'vga',
                   'guestmachine': 'pseries',
                   'rhelnewest': '',
                   'rhelalt': '',
                  }

HOME_PATH = os.getcwd()

TFTPPATH = "/var/lib/tftpboot"


def clean_env(diskpath, logger):
    if os.path.exists(diskpath):
        os.remove(diskpath)

    if os.path.exists(TFTPPATH):
        shutil.rmtree(TFTPPATH)

    cmd = "virsh net-list --all | grep \'pxeboot\'"
    ret = process.run(cmd, shell=True, ignore_status=True)
    if not ret.exit_status:
        logger.info("remove network pxeboot")
        cmd = "virsh net-destroy pxeboot"
        ret = process.run(cmd, shell=True, ignore_status=True)
        if ret.exit_status:
            logger.error("failed to destroy network pxeboot")
            logger.error("%s" % ret.stdout)
        else:
            cmd = "virsh net-undefine pxeboot"
            ret = process.run(cmd, shell=True, ignore_status=True)
            if ret.exit_status:
                logger.error("failed to undefine network pxeboot")
                logger.error("%s" % ret.stdout)


def prepare_conf_ppc(ostree, kscfg, newest, envparser):
    os.system("restorecon -Rv %s >> /dev/null 2>&1" % TFTPPATH)

    if newest is None:
        new_boot_cfg_filename = TFTPPATH + '/tmp.conf'
        new_boot_cfg = open(new_boot_cfg_filename, 'w')
        if 'RHEL-6' in ostree:
            old_boot_cfg_filename = TFTPPATH + '/etc/yaboot.conf'
            old_boot_cfg = open(old_boot_cfg_filename, 'r')

            for line in old_boot_cfg:
                if re.search('timeout', line):
                    line = "timeout=5\n"
                new_boot_cfg.write(line)
            line = ('\tappend= "ks=%s"\n' % (kscfg))
            new_boot_cfg.write(line)
        else:
            old_boot_cfg_filename = TFTPPATH + '/boot/grub/grub.cfg'
            old_boot_cfg = open(old_boot_cfg_filename, 'r')

            for line in old_boot_cfg:
                if re.search(r'linux /ppc/ppc64/vmlinuz  ro', line):
                    line = line.replace('ro', 'inst.repo=%s inst.ks=%s ro' % (ostree, kscfg))
                new_boot_cfg.write(line)
        new_boot_cfg.close()
        old_boot_cfg.close()
        shutil.move(new_boot_cfg_filename, old_boot_cfg_filename)
    else:
        if 'RHEL-ALT' in newest:
            arch = re.search(r'ppc.*?/', ostree).group()[:-1]
            bootaddr = envparser.get_value('guest', 'rhel_alt7_' + arch + '_boot')
            cmd = 'wget -N ' + bootaddr + ' -P ' + TFTPPATH + '/boot/grub/'
            ret = process.run(cmd, shell=True, ignore_status=True)
        elif 'RHEL' in newest:
            if 'RHEL-6' in ostree:
                bootaddr = envparser.get_value('guest', 'rhel6_ppc64_boot')
                cmd = 'wget -N ' + bootaddr + ' -P ' + TFTPPATH + '/etc/'
            else:
                arch = re.search(r'ppc.*?/', ostree).group()[:-1]
                bootaddr = envparser.get_value('guest', 'rhel7_' + arch + '_boot')
                cmd = 'wget -N ' + bootaddr + ' -P ' + TFTPPATH + '/boot/grub/'
            ret = process.run(cmd, shell=True, ignore_status=True)


def prepare_network_ppc(ostree, logger):
    xmlpath = os.path.join(HOME_PATH, 'repos/installation/xmls/pxeboot.xml')
    xml_fp = open(xmlpath, 'r')
    tmppath = os.path.join(HOME_PATH, 'repos/installation/xmls/tmp.xml')
    tmp_fp = open(tmppath, 'w')
    prodlist = ['RHEL', 'RHEL-ALT']

    for line in xml_fp:
        r = re.match(r'<bootp file=', line)
        if (r is not None) and any(i for i in prodlist if i in ostree):
            line = '<bootp file="boot/grub/powerpc-ieee1275/core.elf" />\n'
        if (r is not None) and ('RHEL-6' in ostree):
            line = '<bootp file="ppc/chrp/yaboot" />\n'
        tmp_fp.write(line)
    tmp_fp.close()
    xml_fp.close()
    shutil.move(tmppath, xmlpath)

    cmd = "virsh net-define %s" % xmlpath
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status != 0:
        logger.error(ret.stdout)

    cmd = "virsh net-start pxeboot"
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status != 0:
        logger.error(ret.stdout)


def prepare_kernel_ppc(ostree, logger):
    if 'RHEL-6' in ostree:
        conf_path = urllib.request.urlopen(ostree + '/etc/').geturl()
    else:
        conf_path = urllib.request.urlopen(ostree + '/boot/').geturl()
    if '/released/' in ostree:
        wget_paramter = "-m -np -nH --cut-dirs=6 -R 'index.html*' -P "
    else:
        wget_paramter = "-m -np -nH --cut-dirs=9 -R 'index.html*' -P "
    wget_command = 'wget ' + wget_paramter + TFTPPATH + ' ' + conf_path
    logger.debug('%s' % (wget_command))
    ret = process.run(wget_command, shell=True, ignore_status=True)
    if ret.exit_status != 0:
        logger.error(ret.stdout)

    ppc_path = urllib.request.urlopen(ostree + '/ppc/').geturl()
    if '/released/' in ostree:
        if 'RHEL-6' in ostree:
            wget_paramter = "-m -np -nH --cut-dirs=6 -R 'index.html*' -A initrd.img,vmlinuz,yaboot -P "
        else:
            wget_paramter = "-m -np -nH --cut-dirs=6 -R 'index.html*' -A initrd.img,vmlinuz -P "
    else:
        wget_paramter = "-m -np -nH --cut-dirs=9 -R 'index.html*' -A initrd.img,vmlinuz -P "
    wget_command = 'wget ' + wget_paramter + TFTPPATH + ' ' + ppc_path
    logger.debug('%s' % (wget_command))
    ret = process.run(wget_command, shell=True, ignore_status=True)
    if ret.exit_status != 0:
        logger.error(ret.stdout)


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


def install_linux_pxe_ppc(params):
    """ install a new virtual machine """
    logger = params['logger']

    guestname = params.get('guestname')
    guestos = params.get('guestos')
    guestarch = params.get('guestarch')
    xmlstr = params['xml']
    nicdriver = params.get('nicdriver', 'virtio')
    hddriver = params.get('hddriver', 'virtio')
    diskpath = params.get('diskpath', '/var/lib/libvirt/images/libvirt-test-api')
    seeksize = params.get('disksize', 14)
    imageformat = params.get('imageformat', 'qcow2')
    graphic = params.get('graphic', 'vnc')
    video = params.get('video', 'vga')
    installtype = params.get('type', 'define')

    logger.info("guestname: %s" % guestname)
    params_info = "%s, %s, " % (guestos, guestarch)
    params_info += "%s(network), %s(disk), " % (nicdriver, hddriver)
    params_info += "%s, %s, " % (imageformat, graphic)
    params_info += "%s, %s(storage)" % (video, 'local')
    logger.info("%s" % params_info)

    xmlstr = xmlstr.replace('GRAPHIC', graphic)
    xmlstr = xmlstr.replace("VIDEO", video)

    conn = sharedmod.libvirtobj['conn']
    check_domain_state(conn, guestname, logger)

    logger.info("disk image is %s" % diskpath)
    clean_env(diskpath, logger)
    if not install_common.create_image(diskpath, seeksize, imageformat, logger):
        return 1

    xmlstr = install_common.set_disk_xml(hddriver, xmlstr, diskpath, logger)

    logger.info("get system environment information")
    envfile = os.path.join(HOME_PATH, 'global.cfg')
    logger.info("the environment file is %s" % envfile)

    os_arch = guestos + "_" + guestarch

    rhelnewest = params.get('rhelnewest')
    rhelalt = params.get('rhelalt')
    logger.info("rhelnewest: %s" % rhelnewest)

    envparser = env_parser.Envparser(envfile)

    ostree = install_common.get_ostree(rhelnewest, guestos, guestarch, logger)
    kscfg = install_common.get_kscfg(rhelnewest, guestos, guestarch, "pxe", logger)
    isolink = install_common.get_iso_link(rhelnewest, guestos, guestarch, logger)

    prepare_kernel_ppc(ostree, logger)
    prepare_network_ppc(ostree, logger)
    prepare_conf_ppc(ostree, kscfg, rhelnewest, envparser)

    logger.debug('dump installation guest xml:\n%s' % xmlstr)

    installtype = params.get('type', 'define')
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
    while(interval < 3600):
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

    if interval == 3600:
        if 'rhel3u9' in guestname:
            logger.info("guest installaton will be destoryed forcelly for rhel3u9 guest")
            domobj.destroy()
            logger.info("boot guest vm off harddisk")
            ret = prepare_boot_guest(domobj, xmlstr, guestname, installtype, logger)
            if ret:
                logger.info("booting guest vm off harddisk failed")
                return 1
        else:
            logger.info("guest installation timeout 3600s")
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


def install_linux_pxe_ppc_clean(params):
    """ clean testing environment """
    logger = params['logger']
    guestname = params.get('guestname')

    diskpath = params.get('diskpath', '/var/lib/libvirt/images/libvirt-test-api')
    conn = libvirt.open()
    domain_common.guest_clean(conn, guestname, logger)

    clean_env(diskpath, logger)
