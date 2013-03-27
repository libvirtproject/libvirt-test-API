#!/usr/bin/env python
#
# Copyright (C) 2010-2012 Red Hat, Inc.
#
# libvirt-test-API is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 2 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranties of
# TITLE, NON-INFRINGEMENT, MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import os
import re
import sys
import time
import random
import commands
import socket
import fcntl
import pty
import signal
import struct
import pexpect
import string
import subprocess
import hashlib
import libvirt
import math
from xml.dom import minidom
from urlparse import urlparse

subproc_flag = 0


def get_hypervisor():
    if commands.getoutput("lsmod | grep kvm"):
        return 'kvm'
    elif os.access("/proc/xen", os.R_OK):
        return 'xen'
    else:
        return 'no any hypervisor is running.'


def get_uri(ip):
    """Get hypervisor uri"""
    hypervisor = get_hypervisor()
    if ip == "127.0.0.1":
        if hypervisor == "xen":
            uri = "xen:///"
        if hypervisor == "kvm":
            uri = "qemu:///system"
    else:
        if hypervisor == "xen":
            uri = "xen+ssh://%s" % ip
        if hypervisor == "kvm":
            uri = "qemu+ssh://%s/system" % ip
    return uri


def request_credentials(credentials, user_data):
    for credential in credentials:
        if credential[0] == libvirt.VIR_CRED_AUTHNAME:
            credential[4] = user_data[0]

            if len(credential[4]) == 0:
                credential[4] = credential[3]
        elif credential[0] == libvirt.VIR_CRED_PASSPHRASE:
            credential[4] = user_data[1]
        else:
            return -1

    return 0


def get_conn(uri='', username='', password=''):
    """ get connection object from libvirt module
    """
    user_data = [username, password]
    auth = [[libvirt.VIR_CRED_AUTHNAME, libvirt.VIR_CRED_PASSPHRASE],
            request_credentials, user_data]
    conn = libvirt.openAuth(uri, auth, 0)
    return conn


def parse_uri(uri):
    # This is a simple parser for uri
    return urlparse(uri)


def get_host_arch():
    ret = commands.getoutput('uname -a')
    arch = ret.split(" ")[-2]
    return arch


def get_local_hostname():
    """ get local host name """
    return socket.gethostname()


def get_libvirt_version(ver=''):
    ver = commands.getoutput("rpm -q libvirt|head -1")
    if ver.split('-')[0] == 'libvirt':
        return ver
    else:
        print "Missing libvirt package!"
        sys.exit(1)


def get_hypervisor_version(ver=''):
    hypervisor = get_hypervisor()

    if 'kvm' in hypervisor:
        kernel_ver = get_host_kernel_version()
        if 'el5' in kernel_ver:
            ver = commands.getoutput("rpm -q kvm")
        elif 'el6' in kernel_ver:
            ver = commands.getoutput("rpm -q qemu-kvm")
        elif 'el7' in kernel_ver:
            ver = commands.getoutput("rpm -q qemu-kvm")
        else:
            print "Unsupported kernel type!"
            sys.exit(1)
    elif 'xen' in hypervisor:
        ver = commands.getoutput("rpm -q xen")
    else:
        print "Unsupported hypervisor type!"
        sys.exit(1)

    return ver


def get_host_kernel_version():
    kernel_ver = commands.getoutput('uname -r')
    return kernel_ver


def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915,  # SIOCGIFADDR
                                        struct.pack('256s', ifname[:15]))[20:24])


def get_host_cpus():
    if not os.access("/proc/cpuinfo", os.R_OK):
        print "warning:os error"
        sys.exit(1)
    else:
        cmd = "cat /proc/cpuinfo | grep '^processor'|wc -l"
        cpus = int(commands.getoutput(cmd))
        if cpus:
            return cpus
        else:
            print "warnning:don't get system cpu number"


def get_host_frequency():
    if not os.access("/proc/cpuinfo", os.R_OK):
        print "warning:os error"
        sys.exit(1)
    else:
        cmd = "cat /proc/cpuinfo | grep 'cpu MHz'|uniq"
        cpufreq = commands.getoutput(cmd)
        if cpufreq:
            freq = cpufreq.split(":")[1].split(" ")[1]
            return freq
        else:
            print "warnning:don't get system cpu frequency"


def get_host_memory():
    if not os.access("/proc/meminfo", os.R_OK):
        print "please check os."
        sys.exit(1)
    else:
        cmd = "cat /proc/meminfo | egrep 'MemTotal'"
        ret = commands.getoutput(cmd)
        strMem = ret.split(":")[1]
        mem_num = strMem.split("kB")[0]
        mem_size = int(mem_num.strip())
        if mem_size:
            return mem_size
        else:
            print "warnning:don't get os memory"


def get_vcpus_list():
    host_cpus = get_host_cpus()
    max_vcpus = host_cpus * 4
    vcpus_list = []
    n = 0
    while 2 ** n <= max_vcpus:
        vcpus_list.append(2 ** n)
        n += 1
    return vcpus_list


def get_memory_list():
    host_mem = get_host_memory()
    mem_list = []
    i = 10
    while 2 ** i * 1024 <= host_mem:
        mem_list.append(2 ** i)
        i += 1
    return mem_list


def get_curr_time():
    curr_time = time.strftime('%Y-%m-%d %H:%M:%S')
    return curr_time


def get_rand_uuid():
    return file('/proc/sys/kernel/random/uuid').readline().strip()


def get_rand_mac():
    mac = []
    mac.append(0x54)
    mac.append(0x52)
    mac.append(0x00)
    i = 0
    while i < 3:
        mac.append(random.randint(0x00, 0xff))
        i += 1
    return ':'.join(map(lambda x: "%02x" % x, mac))


def get_dom_mac_addr(domname):
    """Get mac address of a domain

       Return mac address on SUCCESS or None on FAILURE
    """
    cmd = \
        "virsh dumpxml " + domname \
        + " | grep 'mac address' | awk -F'=' '{print $2}' | tr -d \"[\'/>]\""

    (ret, out) = commands.getstatusoutput(cmd)
    if ret == 0:
        return out
    else:
        return None


def get_num_vcpus(domname):
    """Get mac address of a domain
       Return mac address on SUCCESS or None on FAILURE
    """
    cmd = "virsh dumpxml " + domname + \
        " | grep 'vcpu' | awk -F'<' '{print $2}' | awk -F'>' '{print $2}'"

    (ret, out) = commands.getstatusoutput(cmd)
    if ret == 0:
        return out
    else:
        return None


def get_size_mem(domname):
    """Get mem size of a domain
       Return mem size on SUCCESS or None on FAILURE
    """
    cmd = "virsh dumpxml " + domname + \
        " | grep 'currentMemory'|awk -F'<' '{print $2}'|awk -F'>' '{print $2}'"

    (ret, out) = commands.getstatusoutput(cmd)
    if ret == 0:
        return out
    else:
        return None


def get_disk_path(dom_xml):
    """Get full path of bootable disk image of domain
       Return mac address on SUCCESS or None on FAILURE
    """
    doc = minidom.parseString(dom_xml)
    disk_list = doc.getElementsByTagName('disk')
    source = disk_list[0].getElementsByTagName('source')[0]
    attribute = source.attributes.keys()[0]

    return source.attributes[attribute].value


def get_capacity_suffix_size(capacity):
    dicts = {}
    change_to_byte = {'K': pow(2, 10), 'M': pow(2, 20), 'G': pow(2, 30),
                      'T': pow(2, 40)}
    for suffix in change_to_byte.keys():
        if capacity.endswith(suffix):
            dicts['suffix'] = suffix
            dicts['capacity'] = capacity.split(suffix)[0]
            dicts['capacity_byte'] = \
                int(dicts['capacity']) * change_to_byte[suffix]
    return dicts


def dev_num(guestname, device):
    """Get disk or interface number in the guest"""
    cur = commands.getoutput("pwd")
    cmd = "sh %s/utils/dev_num.sh %s %s" % (cur, guestname, device)
    num = int(commands.getoutput(cmd))
    if num:
        return num
    else:
        return None


def stop_selinux():
    selinux_value = commands.getoutput("getenforce")
    if selinux_value == "Enforcing":
        os.system("setenforce 0")
        if commands.getoutput("getenforce") == "Permissive":
            return "selinux is disabled"
        else:
            return "Failed to stop selinux"
    else:
        return "selinux is disabled"


def stop_firewall(ip):
    stopfire = ""
    if ip == "127.0.0.1":
        stopfire = commands.getoutput("service iptables stop")
    else:
        stopfire = commands.getoutput("ssh %s service iptables stop") % ip
    if stopfire.find("stopped"):
        print "Firewall is stopped."
    else:
        print "Failed to stop firewall"
        sys.exit(1)


def print_section(title):
    print "\n%s" % title
    print "=" * 60


def print_entry(key, value):
    print "%-10s %-10s" % (key, value)


def print_xml(key, ctx, path):
    res = ctx.xpathEval(path)
    if res is None or len(res) == 0:
        value = "Unknown"
    else:
        value = res[0].content
    print_entry(key, value)
    return value


def print_title(info, delimiter, num):
    curr_time = get_curr_time()
    blank = ' ' * (num / 2 - (len(info) + 8 + len(curr_time)) / 2)
    print delimiter * num
    print "%s%s\t%s" % (blank, info, curr_time)
    print delimiter * num


def file_read(file):
    if os.path.exists(file):
        fh = open(file, 'r')
        theData = fh.read()
        fh.close()
        return theData
    else:
        print "The FILE %s doesn't exist." % file


def parse_xml(file, element):
    xmldoc = minidom.parse(file)
    elementlist = xmldoc.getElementsByTagName(element)
    return elementlist


def locate_utils():
    """Get the directory path of 'utils'"""
    pwd = os.getcwd()
    result = re.search('(.*)libvirt-test-API(.*)', pwd)
    return result.group(0) + "/utils"


def mac_to_ip(mac, timeout, br='virbr0'):
    """Map mac address to ip under a specified brige

       Return None on FAILURE and the mac address on SUCCESS
    """
    if not mac:
        return None

    if timeout < 10:
        timeout = 10

    cmd = "sh " + locate_utils() + "/ipget.sh " + mac + " " + br

    while timeout > 0:
        (ret, out) = commands.getstatusoutput(cmd)
        if not out.lstrip() == "":
            break

        timeout -= 10

    return timeout and out or None


def do_ping(ip, timeout):
    """Ping some host

       return True on success or False on Failure
       timeout should be greater or equal to 10
    """
    if not ip:
        return False

    if timeout < 10:
        timeout = 10

    cmd = "ping -c 3 " + str(ip)

    while timeout > 0:
        (ret, out) = commands.getstatusoutput(cmd)
        if ret == 0:
            break
        timeout -= 10

    return (timeout and 1) or 0


def exec_cmd(
        command,
        sudo=False,
        cwd=None,
        infile=None,
        outfile=None,
        shell=False,
        data=None):
    """
    Executes an external command, optionally via sudo.
    """
    if sudo:
        if isinstance(command, type("")):
            command = "sudo " + command
        else:
            command = ["sudo"] + command
    if infile is None:
        infile = subprocess.PIPE
    if outfile is None:
        outfile = subprocess.PIPE
    p = subprocess.Popen(command, shell=shell, close_fds=True, cwd=cwd,
                         stdin=infile, stdout=outfile, stderr=subprocess.PIPE)
    (out, err) = p.communicate(data)
    if out is None:
        # Prevent splitlines() from barfing later on
        out = ""
    return (p.returncode, out.splitlines())


def remote_exec_pexpect(hostname, username, password, cmd):
    """ Remote exec function via pexpect """
    user_hostname = "%s@%s" % (username, hostname)
    child = pexpect.spawn("/usr/bin/ssh", [user_hostname, cmd],
                          timeout=60, maxread=2000, logfile=None)
    while True:
        index = child.expect(['(yes\/no)', 'password:', pexpect.EOF,
                              pexpect.TIMEOUT])
        if index == 0:
            child.sendline("yes")
        elif index == 1:
            child.sendline(password)
        elif index == 2:
            child.close()
            return 0, string.strip(child.before)
        elif index == 3:
            child.close()
            return 1, "Timeout!!!!"

    return 0


def scp_file(hostname, username, password, target_path, file):
    """ Scp file to remote host """
    user_hostname = "%s@%s:%s" % (username, hostname, target_path)
    child = pexpect.spawn("/usr/bin/scp", [file, user_hostname])
    while True:
        index = child.expect(['yes\/no', 'password: ',
                              pexpect.EOF,
                              pexpect.TIMEOUT])
        if index == 0:
            child.sendline("yes")
        elif index == 1:
            child.sendline(password)
        elif index == 2:
            child.close()
            return 0
        elif index == 3:
            child.close()
            return 1

    return 0


def support_virt(self):
    cmd = "cat /proc/cpuinfo | egrep '(vmx|svm)'"
    if commands.getoutput(cmd) is None:
        print 'CPU does not support VT.'
        return False
    else:
        return True


def subproc(a, b):
    global subproc_flag
    subproc_flag = 1


def remote_exec(hostname, username, password, cmd):
    """Remote execution on specified host"""
    global subproc_flag
    pid, fd = pty.fork()
    if pid == 0:
        try:
            os.execv("/usr/bin/ssh", ["/usr/bin/ssh", "-l",
                                      username, hostname, cmd])
        except OSError as e:
            print "OSError: " + str(e)
            return -1
    else:
        signal.signal(signal.SIGCHLD, subproc)
        try:
            timeout = 50
            i = 0
            while i <= timeout:

                time.sleep(1)
                str = os.read(fd, 10240)

                if re.search('(yes\/no)', str):
                    os.write(fd, "yes\r")

                elif re.search('password:', str):
                    os.write(fd, password + "\r")

                elif subproc_flag == 1:
                    ret = string.strip(str)
                    break
                elif i == timeout:
                    print "TIMEOUT!!!!"
                    return -1

                i = i + 1

            subproc_flag = 0
            return ret
        except Exception as e:
            print e
            subproc_flag = 0
            return -1


def get_remote_vcpus(hostname, username, password):
    """Get cpu number of specified host"""
    cmd = "cat /proc/cpuinfo | grep processor | wc -l"
    cpunum = -1
    i = 0
    while i < 3:
        i += 1
        cpunum = int(remote_exec(hostname, username, password, cmd))
        if cpunum == -1:
            continue
        else:
            break
    return cpunum


def get_remote_memory(hostname, username, password):
    """Get memory statics of specified host"""
    cmd = "free -m | grep -i mem | awk '{print $2}'"
    memsize = -1
    i = 0
    while i < 3:
        i += 1
        ret, out = remote_exec_pexpect(hostname, username, password, cmd)
        memsize = int(out) * 1024
        if memsize == -1:
            continue
        else:
            break
    return memsize


def get_remote_kernel(hostname, username, password):
    """Get kernel info of specified host"""
    cmd = "uname -r"
    kernel = None
    i = 0
    while i < 3:
        i += 1
        kernel = remote_exec(hostname, username, password, cmd)
        if kernel:
            break
        else:
            continue
    return kernel


def install_package(package=''):
    """Install specified package"""
    if package:
        cmd = "rpm -qa " + package
        output = commands.getoutput(cmd)
        pkg = output.split('\n')[0]
        if pkg:
            os.system("yum -y -q update " + package)
            return pkg
        else:
            ret = os.system("yum -y -q install " + package)
            if ret == 0:
                output = commands.getoutput(cmd)
                pkg = output.split('\n')[0]
                if pkg:
                    return pkg
            else:
                return "failed to install package"
    else:
        return "please input package name"


def libvirt_version(latest_ver=''):
    """Get libvirt version info"""
    query_virt_ver = 'rpm -qa|grep libvirt'
    ret = commands.getoutput(query_virt_ver)
    if ret:
        mas_ver = ret.split('-')[-2]
        sec_ver = (ret.split('-')[-1])
        curr_ver = mas_ver + '-' + sec_ver
        if latest_ver != '':
            if curr_ver != latest_ver:
                return (False, curr_ver)
            else:
                return (True, curr_ver)
        else:
            return curr_ver
    else:
        return (False, '')


def create_dir(hostname, username, password):
    """Create new dir"""
    cmd = "mkdir /tmp/test"
    ret, mkdir_ret = remote_exec_pexpect(hostname, username, password, cmd)
    if mkdir_ret == '':
        cmd = "ls -d /tmp/test"
        ret, check_str = remote_exec_pexpect(hostname, username,
                                             password, cmd)
        if check_str == "/tmp/test":
            return 0
        else:
            print "check_str = ", check_str
            return 1
    else:
        print "mkdir_ret = ", mkdir_ret
        return 1


def write_file(hostname, username, password):
    """Simple test for writting file on specified host"""
    test_string = 'hello word testing'
    cmd = """echo '%s'>/tmp/test/test.log""" % (test_string)
    ret, write_file_ret = remote_exec_pexpect(hostname, username,
                                              password, cmd)
    if write_file_ret == '':
        cmd = """grep '%s' /tmp/test/test.log""" % ("hello")
        ret, check_str = remote_exec_pexpect(hostname, username,
                                             password, cmd)
        if check_str == test_string:
            return 0
        else:
            print "check_str = ", check_str
            return 1
    else:
        print "write_file_ret = ", write_file_ret
        return 1


def run_mount_app(hostname, username, password,
                  target_mount, mount_point):
    """Simple test for mount operation on specified host"""
    cmd = """mount %s %s""" % (target_mount, mount_point)
    mount_ret = remote_exec(hostname, username, password, cmd)
    if mount_ret == '':
        cmd = """df | grep '%s'""" % (target_mount)
        check_str = remote_exec(hostname, username, password, cmd)
        if check_str != '':
            return 0
        else:
            print "mount check fail"
            return 1
    else:
        print "mount fail"
        return 1


def format_parammap(paramlist, map_test, length):
    """paramlist contains numbers which can be divided by '-', '^' and
       ',', map_test is a tuple for getting it's content (True or False)
       and form the new tuple base on numbers in paramlist, length is
       the length of the return tuple
    """
    parammap = ()

    try:
        if re.match('\^', paramlist):
            unuse = int(re.split('\^', paramlist)[1])
            for i in range(length):
                if i == unuse:
                    parammap += (False,)
                else:
                    parammap += (map_test[i],)

        elif '-' in paramlist:
            param = re.split('-', paramlist)
            if not len(param) == 2:
                return False
            if not int(param[1]) < length:
                print "paramlist: out of max range"
                return False
            if int(param[1]) < int(param[0]):
                return False

            for i in range(length):
                if i in range(int(param[0]), int(param[1]) + 1):
                    parammap += (True,)
                else:
                    parammap += (map_test[i],)

        else:
            for i in range(length):
                if i == int(paramlist):
                    parammap += (True,)
                else:
                    parammap += (map_test[i],)

        return parammap
    except ValueError as e:
        print "ValueError: " + str(e)
        return False


def param_to_tuple(paramlist, length):
    """paramlist contains numbers which can be divided by '-', '^' and
       ',', length is the length of the return tuple, return tuple only
       have True or False value
    """
    map_test = ()
    for i in range(length):
        map_test += (False,)

    if ',' in paramlist:
        param = re.split(',', paramlist)
        for i in range(len(param)):
            parammap = format_parammap(param[i], map_test, length)
            if parammap:
                map_test = parammap
            else:
                return False
        return parammap

    else:
        parammap = format_parammap(paramlist, map_test, length)
        if parammap:
            return parammap
        else:
            return False


def digest(path, offset, length):
    """read data from file with length bytes, begin at offset
       and return md5 hexdigest
    """
    f = open(path, 'r')
    f.seek(offset)
    m = hashlib.md5()
    done = 0

    while True:
        want = 1024
        if length and length - done < want:
            want = length - done
        outstr = f.read(want)
        got = len(outstr)
        if got == 0:
            break
        done += got
        m.update(outstr)

    f.close()
    return m.hexdigest()


def run_wget_app(hostname, username, password, file_url, logger):
    """Simple test for wget app on specified host"""
    cmd_line = "wget -P /tmp %s -o /tmp/wget.log" % (file_url)
    logger.info("Command: %s" % (cmd_line))
    ret, wget_ret = remote_exec_pexpect(hostname, username,
                                        password, cmd_line)
    cmd_line = "grep %s %s" % ('100%', '/tmp/wget.log')
    ret, check_ret = remote_exec_pexpect(hostname, username,
                                         password, cmd_line)
    if check_ret == "":
        logger.info("grep output is nothing")
        return 1
    else:
        if re.search("100%", check_ret):
            logger.info("wget is running successfully")
            logger.info("check_retrun: %s" % (check_ret))
            return 0
        else:
            logger.info("can not find 100% in wget output")
            logger.info("check_retrun: %s" % (check_ret))
            return 1


def validate_remote_nic_type(hostname, username,
                             password, nic_type, logger):
    """Validate network interface type on specified host"""
    nic_type_to_name_dict = {'e1000':
                             '82540EM Gigabit Ethernet Controller',
                             'rtl8139':
                             'RTL-8139/8139C/8139C+',
                             'virtio': 'Virtio network device'}
    nic_type_to_driver_dict = {'e1000': 'e1000', 'rtl8139': '8139cp',
                               'virtio': 'virtio_net'}
    nic_name = nic_type_to_name_dict[nic_type]
    nic_driver = nic_type_to_driver_dict[nic_type]
    logger.info("nic_name = %s" % (nic_name))
    logger.info("nic_driver = %s" % (nic_driver))
    lspci_cmd = "lspci"
    lsmod_cmd = "lsmod"
    ret, lspci_cmd_ret = remote_exec_pexpect(hostname, username,
                                             password, lspci_cmd)
    ret, lsmod_cmd_ret = remote_exec_pexpect(hostname, username,
                                             password, lsmod_cmd)
    logger.info("------------")
    logger.info("lspci_cmd_ret:\n %s" % (lspci_cmd_ret))
    logger.info("------------")
    logger.info("lsmod_cmd_ret:\n %s" % (lsmod_cmd_ret))
    logger.info("------------")
    if lspci_cmd_ret != "" and lsmod_cmd_ret != "":
        cmd1 = """echo "%s" | grep '%s'""" % (lspci_cmd_ret, nic_name)
        cmd2 = """echo "%s" | grep '%s'""" % (lsmod_cmd_ret, nic_driver)
        status1, output1 = commands.getstatusoutput(cmd1)
        status2, output2 = commands.getstatusoutput(cmd2)
        if status1 == 0 and status2 == 0:
            # other nic should not be seen in guest
            nic_type_to_name_dict.pop(nic_type)
            for key in nic_type_to_name_dict.keys():
                logger.info("now try to grep other nic type \
                            in lspci output: %s" % key)
                other_name_cmd = """echo '%s' | grep '%s'""" % \
                                 (lspci_cmd_ret, nic_type_to_name_dict[key])
                ret, out = commands.getstatusoutput(other_name_cmd)
                if ret == 0:
                    logger.info("unspecified nic name is seen in \
                               guest's lspci command: \n %s \n" % out)
                    return 1

            nic_type_to_driver_dict.pop(nic_type)
            for key in nic_type_to_driver_dict.keys():
                logger.info("now try to grep other nic type \
                          in lsmod output: %s" % key)
                other_driver_cmd = """echo '%s' | grep '%s'""" % \
                    (lsmod_cmd_ret,
                     nic_type_to_driver_dict[key])
                ret1, out1 = commands.getstatusoutput(other_driver_cmd)
                if ret1 == 0:
                    logger.info("unspecified nic driver is seen \
                               in guest's lsmod command: %s" % out)
                    return 1

            logger.info("lspci ouput about nic is: \n %s; \n \
                        lsmod output about nic is \n %s \n" %
                        (output1, output2))
            return 0
        else:
            logger.info("lspci and lsmod and grep fail")
            return 1
    else:
        logger.info("lspci and lsmod return nothing")
        return 1


def validate_remote_blk_type(hostname, username, password,
                             blk_type, logger):
    """Validate block device type on specified host"""
    blk_type_to_name_dict = {'ide': 'Intel Corporation 82371SB PIIX3 IDE',
                             'virtio': 'Virtio block device'}
    blk_type_to_driver_dict = {'ide': 'unknow', 'virtio': 'virtio_blk'}
    lspci_cmd = "lspci"
    lsmod_cmd = "lsmod"
    ret, lspci_cmd_ret = remote_exec_pexpect(hostname, username,
                                             password, lspci_cmd)
    ret, lsmod_cmd_ret = remote_exec_pexpect(hostname, username,
                                             password, lsmod_cmd)
    logger.info("------------")
    logger.info("lspci_cmd_ret:\n %s" % (lspci_cmd_ret))
    logger.info("------------")
    logger.info("lsmod_cmd_ret: \n %s" % (lsmod_cmd_ret))
    logger.info("------------")
    if lspci_cmd_ret != "" and lsmod_cmd_ret != "":
        if blk_type == "virtio":
            blk_name = blk_type_to_name_dict[blk_type]
            blk_driver = blk_type_to_driver_dict[blk_type]
            logger.info("blk_name = %s \n blk_driver = %s" %
                        (blk_name, blk_driver))
            cmd1 = """echo "%s" | grep '%s'""" % (lspci_cmd_ret, blk_name)
            cmd2 = """echo "%s" | grep '%s'""" % (lsmod_cmd_ret, blk_driver)
            status1, output1 = commands.getstatusoutput(cmd1)
            status2, output2 = commands.getstatusoutput(cmd2)
            if status1 == 0 and status2 == 0:
                logger.info("block device type is virtio")
                return 0
            else:
                return 1

        # this check will not check ide type block device
        if blk_type == "ide":
            # virtio block device should not be seen in guest
            blk_type_to_name_dict.pop(blk_type)
            for key in blk_type_to_name_dict.keys():
                logger.info(
                    "now try to grep other blk type in lspci output: %s" %
                    key)
                other_name_cmd = """echo "%s" | grep '%s'""" % \
                                 (lspci_cmd_ret, blk_type_to_name_dict[key])
                ret, out = commands.getstatusoutput(other_name_cmd)
                if ret == 0:
                    logger.info("unspecified blk name is seen in guest's \
                                lspci command: \n %s \n" % out)
                    return 1
            blk_type_to_driver_dict.pop(blk_type)
            for key in blk_type_to_driver_dict.keys():
                logger.info(
                    "now try to grep other blk type in lsmod output: %s" %
                    key)
                other_driver_cmd = """echo '%s' | grep '%s'""" % \
                                   (lsmod_cmd_ret,
                                    blk_type_to_driver_dict[key])
                ret1, out1 = commands.getstatusoutput(other_driver_cmd)
                if ret1 == 0:
                    logger.info("unspecified blk driver is seen \
                                in guest's lsmod command: \n %s \n" % out)
                    return 1
            logger.info("block device type is ide")
            return 0
    else:
        logger.info("lspci and lsmod return nothing")
        return 1


def get_standard_deviation(cb1, cb2, opaque1, opaque2, number=1000):
    """ pass two callback functions and opaque return Standard Deviation,
        this function will be useful when need equal some quick change
        value (like memory, cputime), default loop times are 1000,
        and notice callback functions cb1 and cb2 should allways success
    """
    D = 0
    for i in range(number):
        a1 = cb1(opaque1)
        b = cb2(opaque2)
        a2 = cb1(opaque1)
        D += ((int(a1) + int(a2)) / 2 - int(b)) ** 2
    return math.sqrt(D / number)


def param_to_tuple_nolength(paramlist):
    """paramlist contains numbers which can be divided by '-', '^' and
       ',', return tuple only have True or False value
    """
    d = []
    a = paramlist.split(',')
    for i in range(len(a)):
        if a[i].find('^') >= 0:
            continue
        d += a[i].split('-')
    lengh = max(d)

    return param_to_tuple(paramlist, int(lengh) + 1)


def parse_mountinfo(string):
    """a helper to parse mountinfo in /proc/self/mountinfo
       and return a list contains multiple dict
    """

    ret = []
    mount_list = string.split("\n")
    for n in mount_list:
        mount_dict = {}
        if n.find("/") > 0:
            tmp = n[:n.find("/")]
            if len(tmp.split()) != 3:
                continue

            if tmp.split()[2].find(":") < 0:
                continue

            mount_dict['devmajor'] = tmp.split()[2].split(":")[0]
            mount_dict['devminor'] = tmp.split()[2].split(":")[1]

            tmp = n[n.find("/") + 1:]

            mount_dict['mountdir'] = tmp.split()[0]

            if tmp.find(" - ") < 0:
                continue

            tmp = tmp.split(" - ")[1]

            mount_dict['mounttype'] = tmp.split()[0]
            if tmp.split()[1].find("/") > 0:
                mount_dict['sourcedir'] = tmp.split()[1]

            ret.append(mount_dict)

    return ret
