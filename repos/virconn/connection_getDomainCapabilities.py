#!/usr/bin/env python
# test getDomainCapabilities() API for libvirtd

import os
import hashlib
import fcntl

from xml.dom import minidom
from libvirt import libvirtError
from src import sharedmod
from utils import utils

required_params = ('emulatorbin', 'arch', 'machine', 'virttype',)
optional_params = {}

QEMU_CAPS = ""
API_FILE = "/tmp/caps_from_api.xml"
CMD = "rm -rf %s"
OVMF = "/usr/share/OVMF/OVMF_CODE.fd"
AAVMF = "/usr/share/AAVMF/AAVMF_CODE.fd"
IOMMU = "/sys/kernel/iommu_groups/"
VFIO = "/dev/vfio/vfio"
KVM = "/dev/kvm"
KVM_CHECK_EXTENSION = 44547
KVM_CAP_IOMMU = 18
maxcpu = 0

drive = True
drive_forma = True
drive_readonly = False
blk_sg_io = False
usb_storage = False
device = False
scsi_generic = False
vfio_pci = False


def clean_env(logger):
    """
    clean testing environment
    """
    status, output = utils.exec_cmd(CMD % API_FILE, shell=True)
    if status != 0:
        logger.error("Can not delete %s" % API_FILE)
    else:
        logger.debug("Deleted %s successfully" % API_FILE)


def get_hypervisor_ver(emulatorbin, logger):
    """
    Obtain qemu-kvm's version, and return a number value of version
    """
    RPM = "rpm -qf %s"
    status, package = utils.exec_cmd(RPM % emulatorbin, shell=True)
    if not status:
        logger.debug("The package is %s" % package)
    else:
        logger.debug("The package is %s" % package)
        return 0
    package = package[0].split('-')
    version = ""
    for item in package:
        if not item.isalnum():
            for v in item.split("."):
                version = version + v.rjust(3, "0")
            break
    return int(version)


def validate_caps_from_hv(emulatorbin, logger):
    """
    Validate the relative caps between libvirt and qemu-kvm
    """
    F1 = "%s -h| grep \"\-drive\""
    F2 = "%s -h| grep \"format=\""
    F3 = "%s -h| grep \"readonly=\""
    F4 = "%s -h| grep \"^\\-device\""
    l = [F1, F2, F3, F4]
    flags = []
    for item in l:
        status, temp = utils.exec_cmd(item % emulatorbin, shell=True)
        if not status:
            flags.append(True)
            logger.debug("Got: %s from vh" % temp)
        else:
            flags.append(False)
            logger.debug("Got: %s from vh" % temp)
    if get_hypervisor_ver(emulatorbin, logger) >= 11000:
        flags.append(True)
    else:
        flags.append(False)

    if not utils.version_compare("libvirt", 1, 3, 5, logger):
        libvirt_f = [drive, drive_forma, drive_readonly, device, blk_sg_io]
        if flags == libvirt_f:
            return True
        else:
            return False
    else:
        return True


def generate_hash(emulatorbin, logger):
    """
    generate file name using sha256
    """
    global QEMU_CAPS
    QEMU_CAPS = "/var/cache/libvirt/qemu/capabilities/"
    file_name = hashlib.sha256(emulatorbin).hexdigest()
    QEMU_CAPS = QEMU_CAPS + file_name + ".xml"
    logger.debug("Cache file is %s" % QEMU_CAPS)


def get_maxcpu(machine, logger):
    """
    return maxcpu for given machine type from QEMU_CAPS xml
    """
    global maxcpu
    xml = minidom.parse(QEMU_CAPS)
    qemu = xml.getElementsByTagName('qemuCaps')[0]
    for item in qemu.getElementsByTagName('machine'):
        if item.getAttribute('name') == machine:
            maxcpu = int(item.getAttribute('maxCpus'))
    return True


def get_os_flags(logger):
    """
    Read results from QEMU_CAPS file and set three flags
    """
    global drive, drive_forma, drive_readonly
    xml = minidom.parse(QEMU_CAPS)
    qemu = xml.getElementsByTagName('qemuCaps')[0]
    if not utils.version_compare("libvirt", 1, 3, 5, logger):
        for item in qemu.getElementsByTagName('flag'):
            if item.getAttribute('name') == "drive-readonly":
                drive_readonly = True
    else:
        drive_readonly = True

    logger.debug("drive = %s" % drive)
    logger.debug("drive_format = %s" % drive_forma)
    logger.debug("drive_readonly = %s" % drive_readonly)
    return True


def get_disk_flags(logger):
    """
    Read results from QEMU_CAPS file and set two flags
    """
    global blk_sg_io, usb_storage
    xml = minidom.parse(QEMU_CAPS)
    qemu = xml.getElementsByTagName('qemuCaps')[0]
    if not utils.version_compare("libvirt", 1, 3, 5, logger):
        for item in qemu.getElementsByTagName('flag'):
            if item.getAttribute('name') == "blk-sg-io":
                blk_sg_io = True
            if item.getAttribute('name') == "usb-storage":
                usb_storage = True
    else:
        blk_sg_io = True
        for item in qemu.getElementsByTagName('flag'):
            if item.getAttribute('name') == "usb-storage":
                usb_storage = True

    logger.debug("blk_sg_io = %s" % blk_sg_io)
    logger.debug("usb_storage = %s" % usb_storage)
    return True


def get_hostdev_flags(logger):
    """
    Read results from QEMU_CAPS file and set three flags
    """
    global device, scsi_generic, vfio_pci
    xml = minidom.parse(QEMU_CAPS)
    if not utils.version_compare("libvirt", 1, 3, 5, logger):
        for item in xml.getElementsByTagName('flag'):
            if item.getAttribute('name') == "device":
                device = True
            if item.getAttribute('name') == "scsi-generic":
                scsi_generic = True
            if item.getAttribute('name') == "vfio-pci":
                vfio_pci = True
    else:
        device = True
        for item in xml.getElementsByTagName('flag'):
            if item.getAttribute('name') == "scsi-generic":
                scsi_generic = True
            if item.getAttribute('name') == "vfio-pci":
                vfio_pci = True

    logger.debug("device = %s" % device)
    logger.debug("scsi_generic = %s" % scsi_generic)
    logger.debug("vfio_pci = %s" % vfio_pci)
    return True


def supportsPassthroughVFIO(logger):
    """
    check the vfio mode
    """
    if not os.path.exists(IOMMU):
        logger.error("File %s is not exist" % IOMMU)
        return False
    if not os.path.exists(VFIO):
        logger.error("Module %s is not exist" % VFIO)
        return False
    if len(os.listdir(IOMMU)) > 0:
        return True
    return False


def supportsPassthroughKVM(logger):
    """
    check the legacy kvm mode
    """
    if not os.path.exists(KVM):
        logger.error("File %s is not exist" % KVM)
        return False
    with open(KVM, "r") as kvmfd:
        if fcntl.ioctl(kvmfd, KVM_CHECK_EXTENSION, KVM_CAP_IOMMU) == 1:
            return True
    return False


def check_common_values(given_list, logger):
    """
    Check path/machine/arch/vcpu parameters
    """
    xml = minidom.parse(API_FILE)
    dom = xml.getElementsByTagName('domainCapabilities')[0]
    # get path/machine/arch/vcpu from xml generated by api
    path = dom.getElementsByTagName('path')[0].childNodes[0].data
    domain = dom.getElementsByTagName('domain')[0].childNodes[0].data
    machine = dom.getElementsByTagName('machine')[0].childNodes[0].data
    arch = dom.getElementsByTagName('arch')[0].childNodes[0].data
    vcpu = dom.getElementsByTagName('vcpu')[0].getAttribute('max')
    #put all of them to a list
    list1 = [str(path), str(machine), str(arch), int(vcpu)]
    logger.debug("Got 4 common parameters: %s" % list1)
    if given_list == list1:
        logger.debug("Checking common value: Pass")
    else:
        logger.debug("Checking common value: Fail")
        return False
    return True


def check_vmf(os_element, logger):
    if os.path.exists(OVMF) and os.path.exists(AAVMF):
        vmf1 = os_element.getElementsByTagName('value')[0]
        vmf2 = os_element.getElementsByTagName('value')[1]
        if AAVMF == vmf1.childNodes[0].data and OVMF == vmf2.childNodes[0].data:
            return True
        else:
            logger.error("AAVMF and OVMF exist but get path %s and %s." % (vmf1, vmf2))
            return False
    elif os.path.exists(OVMF) and not os.path.exists(AAVMF):
        vmf = os_element.getElementsByTagName('value')[0]
        if OVMF == vmf.childNodes[0].data:
            return True
        else:
            logger.error("OVMF exist but get path %s." % vmf)
            return False
    elif not os.path.exists(OVMF) and os.path.exists(AAVMF):
        vmf = os_element.getElementsByTagName('value')[0]
        if AAVMF == vmf.childNodes[0].data:
            return True
        else:
            logger.error("AAVMF exist but get path %s." % vmf)
            return False
    else:
        return True


# src/qemu/qemu_capabilites.c/virQEMUCapsFillDomainOSCaps()
def check_os(arch, logger):
    """
       check the os part
    """
    alltype = ["rom", "pflash"]
    allreadonly = ["yes", "no"]
    type_api = []
    readonly_api = []
    xml = minidom.parse(API_FILE)
    dom = xml.getElementsByTagName('domainCapabilities')[0]
    os_element = dom.getElementsByTagName('os')[0]
    loader = os_element.getElementsByTagName('loader')[0]
    if not check_vmf(os_element, logger):
        return False

    enum = loader.getElementsByTagName('enum')
    for item in enum:
        if item.getAttribute('name') == "type":
            value = item.getElementsByTagName("value")
            for temp in value:
                type_api.append(str(temp.childNodes[0].data))
        if item.getAttribute('name') == "readonly":
            value = item.getElementsByTagName("value")
            for temp in value:
                readonly_api.append(str(temp.childNodes[0].data))
    if not (drive & drive_forma):
        alltype.remove("pflash")
    if not drive_readonly:
        allreadonly = []
    logger.debug("Got type list: %s" % type_api)
    logger.debug("Got readonly list: %s" % readonly_api)
    if not type_api == alltype:
        return False
    if not readonly_api == allreadonly:
        return False
    return True


# src/qemu/qemu_capabilites.c/virQEMUCapsFillDomainDeviceDiskCaps()
def check_disk(logger):
    """
    check the disk part in <devices>
    """
    alldevice = ["disk", "cdrom", "floppy", "lun"]
    allbus = ["ide", "fdc", "scsi", "virtio", "usb"]
    device_api = []
    bus_api = []
    xml = minidom.parse(API_FILE)
    dom = xml.getElementsByTagName('domainCapabilities')[0]
    devices = dom.getElementsByTagName('devices')[0]
    disk = devices.getElementsByTagName('disk')[0]
    enum = disk.getElementsByTagName('enum')
    for item in enum:
        if item.getAttribute('name') == "diskDevice":
            value = item.getElementsByTagName("value")
            for temp in value:
                device_api.append(str(temp.childNodes[0].data))
        if item.getAttribute('name') == "bus":
            value = item.getElementsByTagName("value")
            for temp in value:
                bus_api.append(str(temp.childNodes[0].data))
    if not blk_sg_io:
        alldevice.remove("lun")
    if not usb_storage:
        allbus.remove("usb")
    logger.debug("Got diskDevice list: %s" % device_api)
    logger.debug("Got bus list: %s" % bus_api)
    if not device_api == alldevice:
        return False
    if not bus_api == allbus:
        return False
    return True


# src/qemu/qemu_capabilites.c/virQEMUCapsFillDomainDeviceHostdevCaps()
def check_hostdev(logger):
    """
    check the hostdev part in <devices>
    """
    allmode = ["subsystem"]
    allpolicy = ["default", "mandatory", "requisite", "optional"]
    allsubsys = ["usb", "pci", "scsi"]
    allbackend = ["default", "default", "vfio", "kvm"]
    mode_api = []
    policy_api = []
    subsys_api = []
    backend_api = []
    caps_api = []
    xml = minidom.parse(API_FILE)
    dom = xml.getElementsByTagName('domainCapabilities')[0]
    devices = dom.getElementsByTagName('devices')[0]
    hostdev = devices.getElementsByTagName('hostdev')[0]
    enum = hostdev.getElementsByTagName('enum')
    for item in enum:
        if item.getAttribute('name') == "mode":
            value = item.getElementsByTagName("value")
            for temp in value:
                mode_api.append(str(temp.childNodes[0].data))
        if item.getAttribute('name') == "startupPolicy":
            value = item.getElementsByTagName("value")
            for temp in value:
                policy_api.append(str(temp.childNodes[0].data))
        if item.getAttribute('name') == "subsysType":
            value = item.getElementsByTagName("value")
            for temp in value:
                subsys_api.append(str(temp.childNodes[0].data))
        if item.getAttribute('name') == "capsType":
            value = item.getElementsByTagName("value")
            for temp in value:
                caps_api.append(str(temp.childNodes[0].data))
        if item.getAttribute('name') == "pciBackend":
            value = item.getElementsByTagName("value")
            for temp in value:
                backend_api.append(str(temp.childNodes[0].data))
    # WIP, we need more codes to check vfio
    if not (drive & device & scsi_generic):
        allsubsys.remove("scsi")
    if not (supportsPassthroughKVM(logger) & device):
        allbackend.remove("default")
        allbackend.remove("kvm")
    if not (supportsPassthroughVFIO(logger) & vfio_pci):
        allbackend.remove("default")
        allbackend.remove("vfio")
    logger.debug("Got mode list: %s" % mode_api)
    logger.debug("Got startupPolicy list: %s" % policy_api)
    logger.debug("Got subsysType list: %s" % subsys_api)
    logger.debug("Got capsType list: %s" % caps_api)
    logger.debug("Got pciBackend list: %s" % backend_api)
    if not mode_api == allmode:
        return False
    if not policy_api == allpolicy:
        return False
    if not subsys_api == allsubsys:
        return False
    if not backend_api == allbackend:
        return False
    return True


def connection_getDomainCapabilities(params):
    """
    test API for getDomainCapabilities in class virConnect
    """
    logger = params['logger']
    emulatorbin = params['emulatorbin']
    arch = params['arch']
    machine = params['machine']
    virttype = params['virttype']

    try:
        logger.info("The specified emulatorbin is %s" % emulatorbin)
        logger.info("The specified architecture is %s" % arch)
        logger.info("The specified machine is %s" % machine)
        logger.info("The specified virttype is %s" % virttype)

        generate_hash(emulatorbin, logger)
        if not os.path.exists(QEMU_CAPS):
            logger.error("cache file, %s is not exist" % QEMU_CAPS)
            return 1
        if not get_maxcpu(machine, logger):
            logger.debug("get maxcpu: Fail")
            return 1
        if not get_os_flags(logger):
            logger.debug("get os: Fail")
            return 1
        if not get_disk_flags(logger):
            logger.debug("get disk: Fail")
            return 1
        if not get_hostdev_flags(logger):
            logger.debug("get hostdev: Fail")
            return 1
        if not validate_caps_from_hv(emulatorbin, logger):
            logger.error("Failed to compare caps")
            return 1
        else:
            logger.debug("Successed to compare caps")

        conn = sharedmod.libvirtobj['conn']
        caps_from_api = conn.getDomainCapabilities(emulatorbin, arch, machine, virttype, 0)

        logger.debug("The return of API: %s" % caps_from_api)
        fd = open(API_FILE, "w+")
        fd.write(caps_from_api)
        fd.flush()

        given_list = [emulatorbin, machine, arch, maxcpu]
        if not check_common_values(given_list, logger):
            logger.info("Failed to validate common elements")
            return 1
        else:
            logger.info("Successed to validate common elements")
        if not check_os(arch, logger):
            logger.info("Failed to validate os block")
            return 1
        else:
            logger.info("Successed to validate os block")
        if not check_disk(logger):
            logger.info("Failed to validate disk block")
            return 1
        else:
            logger.info("Successed to validate disk block")
        if not check_hostdev(logger):
            logger.info("Failed to validate hostdev block")
            return 1
        else:
            logger.info("Successed to validate hostdev block")

    except libvirtError as e:
        logger.error("API error message: %s" % e.message)
        clean_env(logger)
        return 1

    clean_env(logger)
    return 0
