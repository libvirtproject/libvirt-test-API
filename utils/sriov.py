import glob
import os
import re

from utils import process


DRIVERS_LIST = ['ixgbe', 'igb', 'be2net', 'mlx4_core', 'enic']
DRIVER_DIR = "/sys/bus/pci/drivers/"


def get_net_status(pci, logger):
    cmd = "cat /sys/class/net/%s/operstate" % pci
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("Get net status failed: %s" % ret)
        return ""
    logger.debug("net status: %s" % ret.stdout)
    return ret.stdout


def get_driver_name(logger):
    for driver_name in DRIVERS_LIST:
        cmd = "lsmod | grep %s" % driver_name
        ret = process.run(cmd, shell=True, ignore_status=True)
        if ret.exit_status:
            logger.error("cmd failed: %s" % cmd)
            return ""
        return driver_name
    return ""


def get_pf(logger):
    driver_name = get_driver_name(logger)
    if not driver_name:
        logger.error("Don't find driver.")
        return ""
    pci_list = glob.glob("%s%s/0000*" % (DRIVER_DIR, driver_name))
    pci_addr = ""
    for pci in pci_list:
        name = os.listdir("%s/net" % pci)[0]
        net_status = get_net_status(name, logger)
        if "up" in net_status:
            pci_addr = pci.split("/")[-1]
            break
    return pci_addr


def create_vf(num, logger):
    pci_addr = get_pf(logger)
    logger.info("pci addr: %s" % pci_addr)
    driver_name = get_driver_name(logger)
    logger.info("driver: %s" % driver_name)
    cmd = "lspci -s %s -vv" % pci_addr
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("cmd failed: %s" % ret)
        return False
    max_vf = int(re.findall(r"Total VFs: (.+?),", ret.stdout)[0]) - 1
    logger.info("max vf number: %s" % max_vf)
    if max_vf < num and num < 0:
        logger.error("vf num %s error." % num)
        return False

    cmd = "cat %s%s/%s/sriov_numvfs" % (DRIVER_DIR, driver_name, pci_addr)
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("cmd failed: %s" % ret)
        return False
    if ret.stdout > num:
        cmd = "echo 0 > %s%s/%s/sriov_numvfs" % (DRIVER_DIR, driver_name, pci_addr)
        ret = process.run(cmd, shell=True, ignore_status=True)
        if ret.exit_status:
            logger.error("set vf num to 0 fail: %s" % ret)
            return False

    cmd = "echo %s > %s%s/%s/sriov_numvfs" % (num, DRIVER_DIR, driver_name, pci_addr)
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("set vf num to %s fail: %s" % (num, ret))
        return False
    return True


def get_vfs_addr(num, logger):
    pci_addr = get_pf(logger)
    driver_name = get_driver_name(logger)
    vf = os.readlink("%s%s/%s/virtfn%s" % (DRIVER_DIR, driver_name, pci_addr, (int(num) - 1)))
    vf_addr = os.path.split(vf)[1]
    logger.info("vf addr: %s" % vf_addr)
    return vf_addr


def get_vf_driver(vf_addr, logger):
    cmd = "readlink /sys/bus/pci/devices/%s/driver/ -f" % vf_addr
    logger.debug("cmd: %s" % cmd)
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status != 0:
        logger.error("cmd result: %s" % ret.stdout)
        return 1
    return os.path.basename(ret.stdout)

