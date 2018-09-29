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
import math
import random
import subprocess
import socket
import fcntl
import pty
import signal
import struct
import pexpect
import hashlib
import libvirt
import math
import lxml
import lxml.etree
import locale

from xml.dom import minidom
from src import env_parser
from . import process

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

try:
    unicode
except NameError:
    unicode = str  # pylint:disable=W0622

subproc_flag = 0


def get_hypervisor():
    cmd = "lsmod | grep kvm"
    result = process.run(cmd, shell=True, ignore_status=True)
    if result.exit_status == 0:
        return 'kvm'
    elif os.access("/proc/xen", os.R_OK):
        return 'xen'
    else:
        return 'no any hypervisor is running.'


def get_uri(ipaddr):
    """Get hypervisor uri"""
    hypervisor = get_hypervisor()
    if ipaddr == "127.0.0.1":
        if hypervisor == "xen":
            uri = "xen:///"
        if hypervisor == "kvm":
            uri = "qemu:///system"
    else:
        if hypervisor == "xen":
            uri = "xen+ssh://%s" % ipaddr
        if hypervisor == "kvm":
            uri = "qemu+ssh://%s/system" % ipaddr
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
    """ This is a simple parser for uri """
    return urlparse(uri)


def get_host_arch():
    """ get local host arch """
    cmd = "uname -a"
    result = process.run(cmd, shell=True, ignore_status=True)
    arch = result.stdout.split(" ")[-2]
    return arch


def get_local_hostname():
    """ get local host name """
    return socket.gethostname()


def get_local_ip():
    """ get local ip address """
    cmd = "hostname -i"
    result = process.run(cmd, shell=True, ignore_status=True)
    ip = result.stdout.split()[0]
    return ip


def get_libvirt_version(ver=''):
    """ get Libvirt version """
    cmd = "rpm -q libvirt|head -1"
    result = process.run(cmd, shell=True, ignore_status=True)
    if result.stdout.split('-')[0] == 'libvirt':
        return result.stdout
    else:
        print("Missing libvirt package!")
        sys.exit(1)


def get_hypervisor_version(ver=''):
    """Get hypervisor version"""
    hypervisor = get_hypervisor()

    if 'kvm' in hypervisor:
        kernel_ver = get_host_kernel_version()
        if 'el5' in kernel_ver:
            output = process.system_output("rpm -q kvm", shell=True, ignore_status=True)
        elif 'el6' in kernel_ver:
            output = process.system_output("rpm -q qemu-kvm", shell=True, ignore_status=True)
        elif 'el7' in kernel_ver:
            output = process.system_output("rpm -q qemu-kvm", shell=True, ignore_status=True)
        else:
            print("Unsupported kernel type!")
            sys.exit(1)
    elif 'xen' in hypervisor:
        output = process.system_output("rpm -q xen", shell=True, ignore_status=True)
    else:
        print("Unsupported hypervisor type!")
        sys.exit(1)

    return output


def get_host_kernel_version():
    """Get host's kernel version"""
    cmd = "uname -r"
    result = process.run(cmd, shell=True, ignore_status=True)
    return result.stdout


def get_ip_address(ifname):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(sock.fileno(), 0x8915,  # SIOCGIFADDR
                                        struct.pack('256s', ifname[:15]))[20:24])


def get_host_cpus():
    if not os.access("/proc/cpuinfo", os.R_OK):
        print("warning:os error")
        sys.exit(1)
    else:
        cmd = "cat /proc/cpuinfo | grep '^processor'|wc -l"
        cpus = int(process.system_output(cmd, shell=True, ignore_status=True))
        if cpus:
            return cpus
        else:
            print("warnning:don't get system cpu number")


def get_host_frequency():
    if not os.access("/proc/cpuinfo", os.R_OK):
        print("warning:os error")
        sys.exit(1)
    else:
        if isPower():
            cmd = cmd = "cat /proc/cpuinfo | grep -E 'cpu MHz|clock' | sort | uniq"
        else:
            cmd = "cat /proc/cpuinfo | grep 'cpu MHz'|uniq"
        output = process.system_output(cmd, shell=True, ignore_status=True)
        if output:
            freq = output.split(":")[1].split(" ")[1]
            return freq
        else:
            print("warnning:don't get system cpu frequency")


def get_host_memory():
    if not os.access("/proc/meminfo", os.R_OK):
        print("please check os.")
        sys.exit(1)
    else:
        cmd = "cat /proc/meminfo | egrep 'MemTotal'"
        output = process.system_output(cmd, shell=True, ignore_status=True)
        str_mem = output.split(":")[1]
        mem_num = str_mem.split("kB")[0]
        mem_size = int(mem_num.strip())
        if mem_size:
            return mem_size
        else:
            print("warnning:don't get os memory")


def get_vcpus_list():
    host_cpus = get_host_cpus()
    max_vcpus = host_cpus * 4
    vcpus_list = []
    num = 0
    while 2**num <= max_vcpus:
        vcpus_list.append(2**num)
        num += 1
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


def get_rand_str(length=32):
    ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    chars = []
    for i in range(16):
        chars.append(random.choice(ALPHABET))
    return chars


def get_dom_mac_addr(domname, conn_uri=""):
    """Get mac address of a domain

       Return mac address on SUCCESS or None on FAILURE
    """
    if conn_uri:
        conn_uri = "-c " + conn_uri
    cmd = ("virsh %s dumpxml %s | grep 'mac address' | "
           "awk -F'=' '{print $2}' | tr -d \"[\'/>]\"" % (conn_uri, domname))
    result = process.run(cmd, shell=True, ignore_status=True)
    if result.exit_status == 0:
        return result.stdout
    else:
        return None


def get_num_vcpus(domname):
    """Get mac address of a domain
       Return mac address on SUCCESS or None on FAILURE
    """
    cmd = ("virsh dumpxml %s | grep 'vcpu' | awk -F'<' '{print $2}'"
           " | awk -F'>' '{print $2}'" % domname)
    result = process.run(cmd, shell=True, ignore_status=True)
    if result.exit_status == 0:
        return result.stdout
    else:
        return None


def get_size_mem(domname):
    """Get mem size of a domain
       Return mem size on SUCCESS or None on FAILURE
    """
    cmd = ("virsh dumpxml %s | grep 'currentMemory'|awk -F'<' '{print $2}'"
           "|awk -F'>' '{print $2}'" % domname)
    result = process.run(cmd, shell=True, ignore_status=True)
    if result.exit_status == 0:
        return result.stdout
    else:
        return None


def get_disk_path(dom_xml):
    """Get full path of bootable disk image of domain
       Return mac address on SUCCESS or None on FAILURE
    """
    doc = minidom.parseString(dom_xml)
    disk_list = doc.getElementsByTagName('disk')
    source = disk_list[0].getElementsByTagName('source')[0]
    attribute = list(source.attributes.keys())[0]

    return source.attributes[attribute].value


def get_capacity_suffix_size(capacity):
    dicts = {}
    change_to_byte = {'K': pow(2, 10), 'M': pow(2, 20), 'G': pow(2, 30),
                      'T': pow(2, 40)}
    for suffix in list(change_to_byte.keys()):
        if capacity.endswith(suffix):
            dicts['suffix'] = suffix
            dicts['capacity'] = capacity.split(suffix)[0]
            dicts['capacity_byte'] = int(dicts['capacity']) * change_to_byte[suffix]
    return dicts


def dev_num(guestname, device):
    """Get disk or interface number in the guest

       Return None on FAILURE and the disk or interface number in the guest on SUCCESS
    """
    if not guestname or not device:
        return None
    cmd = "virsh dumpxml %s" % guestname
    result = process.run(cmd, shell=True, ignore_status=True)
    if result.exit_status != 0:
        print("failed to dump the xml description of the domain %s." % guestname)
        return None
    guestdump = result.stdout
    device = "</%s>" % device
    num = guestdump.count(device)
    if num:
        return num
    else:
        print("no %s in the domain %s, can you image that?" % (device, guestname))
        return None


def stop_selinux():
    cmd = "getenforce"
    selinux_value = process.system_output(cmd, shell=True, ignore_status=True)
    if selinux_value == "Enforcing":
        os.system("setenforce 0")
        if process.system_output(cmd, shell=True, ignore_status=True) == "Permissive":
            return "selinux is disabled"
        else:
            return "Failed to stop selinux"
    else:
        return "selinux is disabled"


def stop_firewall(ip):
    output = ""
    if ip == "127.0.0.1":
        cmd = "service iptables stop"
    else:
        cmd = "ssh %s service iptables stop" % ip
    output = process.system_output(cmd, shell=True, ignore_status=True)
    if output.find("stopped"):
        print("Firewall is stopped.")
    else:
        print("Failed to stop firewall")
        sys.exit(1)


def print_section(title):
    print("\n%s" % title)
    print("=" * 60)


def print_entry(key, value):
    print("%-10s %-10s" % (key, value))


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
    blank = ' '*(num/2 - (len(info) + 8 + len(curr_time))/2)
    print(delimiter * num)
    print("%s%s\t%s" % (blank, info, curr_time))
    print(delimiter * num)


def file_read(filename):
    if os.path.exists(filename):
        fhandle = open(filename, 'r')
        data = fhandle.read()
        fhandle.close()
        return data
    else:
        print("The FILE %s doesn't exist." % filename)


def parse_xml(filename, element):
    xmldoc = minidom.parse(filename)
    elementlist = xmldoc.getElementsByTagName(element)
    return elementlist


def locate_utils():
    """Get the directory path of 'utils'"""
    pwd = os.getcwd()
    result = re.search('(.*)libvirt-test-API(.*)', pwd)
    return result.group(0) + "/utils"


def mac_to_ip(mac, timeout, bridge='virbr0'):
    """Map mac address to ip under a specified brige

       Return None on FAILURE and the ip address on SUCCESS
    """
    ips = mac_to_ips(mac, timeout, bridge)

    if ips is None or len(ips) == 0:
        return None
    else:
        return ips[0]


def get_bridge_ip(bridge):
    """Get ip addresses binded to a brige

       Return None on FAILURE and the ip address on SUCCESS
    """
    cmd = "ip route"
    result = process.run(cmd, shell=True, ignore_status=True)
    ips = re.findall(r'(\d{1,3}(?:\.\d{1,3}){3}/\d{1,3}) dev %s'
                     % bridge, result.stdout, re.IGNORECASE)

    return ips[0] if ips else None


def mac_to_ips(mac, timeout, bridge='virbr0'):
    """Get all ip addresses binded to a mac under a specified brige

       Return None on FAILURE and the ip address on SUCCESS
    """
    if not mac:
        return None

    bridge_ip = get_bridge_ip(bridge)
    if not bridge_ip:
        return None

    if timeout < 10:
        timeout = 10

    cmd = "nmap -sP -n %s" % bridge_ip
    while timeout > 0:
        result = process.run(cmd, shell=True, ignore_status=True)
        if result.exit_status != 0:
            print("Failed to run nmap command.")
            return None

        ipaddr = re.findall(r'Nmap scan report for ([0-9\.]*)\n.*?\n.*?%s'
                            % mac, result.stdout, re.IGNORECASE)
        if len(ipaddr) > 0:
            break

        time.sleep(10)
        timeout -= 10

    return timeout and ipaddr or None


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
        result = process.run(cmd, shell=True, ignore_status=True)
        if result.exit_status == 0:
            break
        timeout -= 10

    return (timeout and 1) or 0


def exec_cmd(command, sudo=False, cwd=None, infile=None, outfile=None,
             errfile=None, shell=False, data=None):
    """
    Executes an external command, optionally via sudo.
    """
    if sudo:
        if isinstance(command, str):
            command = "sudo " + command
        else:
            command = ["sudo"] + command
    if infile is None:
        infile = subprocess.PIPE
    if outfile is None:
        outfile = subprocess.PIPE
    if errfile is None:
        errfile = subprocess.STDOUT
    process = subprocess.Popen(command, shell=shell, close_fds=True, cwd=cwd,
                               stdin=infile, stdout=outfile, stderr=errfile)
    (out, err) = process.communicate(data)
    if out is None:
        # Prevent splitlines() from barfing later on
        out = ""
    if isinstance(out, str):
        return (process.returncode, out.splitlines())
    else:
        return (process.returncode, out.decode().splitlines())


def remote_exec_pexpect(hostname, username, password, cmd, timeout=30):
    """ Remote exec function via pexpect """
    user_hostname = "%s@%s" % (username, hostname)
    while True:
        child = pexpect.spawn("/usr/bin/ssh", [user_hostname, '-q', cmd],
                              timeout=60, maxread=2000, logfile=None)
        while True:
            index = child.expect(['(yes\/no)', 'password:', pexpect.EOF,
                                  'ssh: connect to host .+ Connection refused',
                                  pexpect.TIMEOUT])
            if index == 0:
                child.sendline("yes")
            elif index == 1:
                child.sendline(password)
            elif index == 2:
                child.close()
                if isinstance(child.before, str):
                    return child.exitstatus, child.before.strip()
                else:
                    return child.exitstatus, child.before.decode().strip()
            elif index == 3:
                if timeout <= 0:
                    return 1, "Refused!!!!"
                time.sleep(5)
                timeout = timeout - 5
                break
            elif index == 4:
                child.close()
                if timeout <= 60:
                    return 1, "Timeout!!!!"
                timeout = timeout - 60
                break


def scp_file(hostname, username, password, target_path, filename):
    """ Scp file to remote host """
    user_hostname = "%s@%s:%s" % (username, hostname, target_path)
    child = pexpect.spawn("/usr/bin/scp", [filename, user_hostname])
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
    if process.system_output(cmd, shell=True, ignore_status=True) is None:
        print('CPU does not support VT.')
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
        except OSError as err:
            print("OSError: " + str(err))
            return -1
    else:
        signal.signal(signal.SIGCHLD, subproc)
        try:
            timeout = 50
            i = 0
            while i <= timeout:
                time.sleep(1)
                output = os.read(fd, 10240)
                if re.search(r'(yes\/no)', output):
                    os.write(fd, "yes\r")
                elif re.search('password:', output):
                    os.write(fd, password + "\r")
                elif subproc_flag == 1:
                    ret = output.decode().strip()
                    break
                elif i == timeout:
                    print("TIMEOUT!!!!")
                    return -1

                i = i + 1

            subproc_flag = 0
            return ret
        except Exception as err:
            print(err)
            subproc_flag = 0
            return -1


def get_remote_vcpus(hostname, username, password, logger):
    """Get cpu number of specified host"""
    cmd = "cat /proc/cpuinfo | grep processor | wc -l"
    (ret, out) = remote_exec_pexpect(hostname, username, password, cmd)
    if ret:
        logger.info("get remote vcpus failed. out: %s" % out)
        return -1
    return out


def get_remote_memory(hostname, username, password, mem_type="DirectMap"):
    """Get memory statics of specified host"""
    cmd = "cat /proc/meminfo | grep %s | awk '{print $2}'" % mem_type
    memsize = -1
    i = 0
    while i < 3:
        i += 1
        ret, out = remote_exec_pexpect(hostname, username, password, cmd)
        memory = out.split('\r\n')
        j = 0
        for j in range(len(memory)):
            memsize += int(memory[j])

        if memsize == -1:
            continue
        else:
            break
    return memsize


def get_remote_kernel(hostname, username, password):
    """Get kernel info of specified host"""
    cmd = "uname -r"
    i = 0
    while i < 3:
        i += 1
        ret, out = remote_exec_pexpect(hostname, username, password, cmd)
        if out:
            break
        else:
            continue
    return out


def install_package(package=''):
    """Install specified package"""
    if package:
        cmd = "rpm -qa " + package
        output = process.system_output(cmd, shell=True, ignore_status=True)
        pkg = output.split('\n')[0]
        if pkg:
            os.system("yum -y -q update " + package)
            return pkg
        else:
            ret = os.system("yum -y -q install " + package)
            if ret == 0:
                output = process.system_output(cmd, shell=True, ignore_status=True)
                pkg = output.split('\n')[0]
                if pkg:
                    return pkg
            else:
                return "failed to install package"
    else:
        return "please input package name"


def libvirt_version(latest_ver=''):
    """Get libvirt version info"""
    cmd = 'rpm -qa|grep libvirt'
    ret = process.system_output(cmd, shell=True, ignore_status=True)
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
            print("check_str = ", check_str)
            return 1
    else:
        print("mkdir_ret = ", mkdir_ret)
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
            print("check_str = ", check_str)
            return 1
    else:
        print("write_file_ret = ", write_file_ret)
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
            print("mount check fail")
            return 1
    else:
        print("mount fail")
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
                print("paramlist: out of max range")
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
    except ValueError as err:
        print("ValueError: " + str(err))
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
    if sys.version_info[0] < 3:
        fhandle = open(path, 'r')
    else:
        fhandle = open(path, 'rb')
    fhandle.seek(offset)
    hash_value = hashlib.md5()
    done = 0

    while True:
        want = 1024
        if length and length - done < want:
            want = length - done
        outstr = fhandle.read(want)
        got = len(outstr)
        if got == 0:
            break
        done += got
        hash_value.update(outstr)

    fhandle.close()
    return hash_value.hexdigest()


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
        ret1 = process.run(cmd1, shell=True, ignore_status=True)
        status1 = ret1.exit_status
        output1 = ret1.stdout
        ret2 = process.run(cmd2, shell=True, ignore_status=True)
        status2 = ret2.exit_status
        output2 = ret2.stdout
        if status1 == 0 and status2 == 0:
            # other nic should not be seen in guest
            nic_type_to_name_dict.pop(nic_type)
            for key in list(nic_type_to_name_dict.keys()):
                logger.info("now try to grep other nic type \
                            in lspci output: %s" % key)
                other_name_cmd = """echo '%s' | grep '%s'""" % \
                                 (lspci_cmd_ret, nic_type_to_name_dict[key])
                name_result = process.run(other_name_cmd, shell=True, ignore_status=True)
                if name_result.exit_status == 0:
                    logger.info("unspecified nic name is seen in \
                               guest's lspci command: \n %s \n" % name_result.stdout)
                    return 1

            nic_type_to_driver_dict.pop(nic_type)
            for key in list(nic_type_to_driver_dict.keys()):
                logger.info("now try to grep other nic type \
                          in lsmod output: %s" % key)
                other_driver_cmd = ("""echo '%s' | grep '%s'""" %
                                    (lsmod_cmd_ret, nic_type_to_driver_dict[key]))
                driver_result = process.run(other_driver_cmd, shell=True, ignore_status=True)
                if driver_result.exit_status == 0:
                    logger.info("unspecified nic driver is seen \
                               in guest's lsmod command: %s" % driver_result.stdout)
                    return 1

            logger.info("lspci ouput about nic is: \n %s; \n"
                        "lsmod output about nic is \n %s \n"
                        % (output1, output2))
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
            ret1 = process.run(cmd1, shell=True, ignore_status=True)
            status1 = ret1.exit_status
            output1 = ret1.stdout
            ret2 = process.run(cmd2, shell=True, ignore_status=True)
            status2 = ret2.exit_status
            output2 = ret2.stdout
            if status1 == 0 and status2 == 0:
                logger.info("block device type is virtio")
                return 0
            else:
                return 1

        # this check will not check ide type block device
        if blk_type == "ide":
            # virtio block device should not be seen in guest
            blk_type_to_name_dict.pop(blk_type)
            for key in list(blk_type_to_name_dict.keys()):
                logger.info(
                    "now try to grep other blk type in lspci output: %s" %
                    key)
                other_name_cmd = """echo "%s" | grep '%s'""" % \
                                 (lspci_cmd_ret, blk_type_to_name_dict[key])
                name_result = process.run(other_name_cmd, shell=True, ignore_status=True)
                if name_result.exit_status == 0:
                    logger.info("unspecified blk name is seen in guest's \
                                lspci command: \n %s \n" % name_result.stdout)
                    return 1
            blk_type_to_driver_dict.pop(blk_type)
            for key in list(blk_type_to_driver_dict.keys()):
                logger.info(
                    "now try to grep other blk type in lsmod output: %s" %
                    key)
                other_driver_cmd = ("""echo '%s' | grep '%s'""" %
                                    (lsmod_cmd_ret, blk_type_to_driver_dict[key]))
                driver_result = process.run(other_driver_cmd, shell=True, ignore_status=True)
                if driver_result.exit_status == 0:
                    logger.info("unspecified blk driver is seen \
                                in guest's lsmod command: \n %s \n" % driver_result.stdout)
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
    param_arr = paramlist.split(',')
    for i in range(len(param_arr)):
        if param_arr[i].find('^') >= 0:
            continue
        d += param_arr[i].split('-')
    lengh = max(d)

    return param_to_tuple(paramlist, int(lengh) + 1)


def parse_mountinfo(info):
    """a helper to parse mountinfo in /proc/self/mountinfo
       and return a list contains multiple dict
    """

    ret = []
    mount_list = info.split("\n")
    for num in mount_list:
        mount_dict = {}
        if num.find("/") > 0:
            tmp = num[:num.find("/")]
            if len(tmp.split()) != 3:
                continue

            if tmp.split()[2].find(":") < 0:
                continue

            mount_dict['devmajor'] = tmp.split()[2].split(":")[0]
            mount_dict['devminor'] = tmp.split()[2].split(":")[1]

            tmp = num[num.find("/") + 1:]

            mount_dict['mountdir'] = tmp.split()[0]

            if tmp.find(" - ") < 0:
                continue

            tmp = tmp.split(" - ")[1]

            mount_dict['mounttype'] = tmp.split()[0]
            if tmp.split()[1].find("/") > 0:
                mount_dict['sourcedir'] = tmp.split()[1]

            ret.append(mount_dict)

    return ret


def check_mac_valid(mac):
    """Check if a mac address is legal"""
    if re.match(r'^[0-9A-F]{2}(:[0-9A-F]{2}){5}$', mac, re.IGNORECASE):
        return True
    return False


def check_address_valid(addr):
    """Check if a address struct is legal """
    try:
        socket.inet_pton(socket.AF_INET, addr['addr'])
        if addr['prefix'] >= 0 and addr['prefix'] <= 32:
            return True
        return False
    except socket.error:
        try:
            socket.inet_pton(socket.AF_INET6, addr['addr'])
            if addr['prefix'] >= 0 and addr['prefix'] <= 128:
                return True
            return False
        except socket.error:
            return False


def check_loop_valid(addr):
    """Check if a loop interface's address is valid"""
    if addr['prefix'] == 128 and addr['addr'] == '::1':
        return True
    if addr['prefix'] == 8 and re.match(r'^127(.\d{1,3}){3}$', addr['addr']):
        return True
    return False


def wait_for(func, timeout, first=0.0, step=1.0):
    """
    Wait until func() evaluates to True.
    If func() evaluates to True before timeout expires, return the
    value of func(). Otherwise return None.
    """
    start_time = time.time()
    end_time = time.time() + float(timeout)
    time.sleep(first)
    while time.time() < end_time:
        output = func()
        if output:
            return output
        time.sleep(step)
    return None


def parse_flags(params, default=0, param_name="flags"):
    """
    Read and generate bitwise-or of given flags.
    return -1 on illegal flag.
    """
    logger = params['logger']
    flags = params.get(param_name, None)
    if flags is None:
        return default

    flag_bit = 0

    for flag in flags.split("|"):
        if flag == 'None':
            # Single None for API with two versoin (with/without flag parameter)
            if len(flags.split("|")) == 1:
                return None
            else:
                logger.error("Flag: 'None' must not be used with other flags!")
                return -1
        elif flag == '0':
            # '0' for API with not used flag
            flag = 0
        else:
            try:
                flag = getattr(libvirt, flag)
            except AttributeError:
                logger.error("Flag:'%s' is illegal or not supported"
                             "by this version of libvirt" % flag)
                return -1
        try:
            flag_bit = flag_bit | flag
        except TypeError:
            logger.error("Flag: '%s' is not a number" % flag)
            return -1

    return flag_bit


def version_compare(package_name, major, minor, update, logger):
    """
    Determine/use the package version on the system
    and compare input major, minor, and update values against it.
    If the running version is greater than or equal to the input
    params version, then return True; otherwise, return False

    This is designed to handle upstream version comparisons for
    test adjustments and/or comparisons as a result of upstream
    fixes or changes that could impact test results.

    :param major: Major version to compare against
    :param minor: Minor version to compare against
    :param update: Update value to compare against
    :return: True if running version is greater than or
                  equal to the input package version
    """
    if package_name == "libvirt-python":
        cmd = "cat /etc/redhat-release"
        ret, out = exec_cmd(cmd, shell=True)
        if ret != 0:
            logger.error("cmd: %s, out: %s" % (cmd, out))
            return False
        if "release 8" in out[0]:
            package_name = "python3-libvirt"

    package_ver = 0
    if package_ver == 0:
        try:
            cmd = "rpm -q %s" % package_name
            ret, out = exec_cmd(cmd, shell=True)
            if ret != 0:
                logger.error("Get %s version failed." % package_name)
                return False

            package = decode_to_text(out[0]).split('-')
            for item in package:
                if not item.isalnum() and ".x86_64" not in item:
                    ver = item.split('.')
                    package_ver = int(ver[0]) * 1000000 + \
                        int(ver[1]) * 1000 + int(ver[2])
                    break
        except (ValueError, TypeError, AttributeError) as err:
            logger.error("Error determining libvirt version: %s" % err)
            return False

    compare_version = major * 1000000 + minor * 1000 + update

    if package_ver >= compare_version:
        return True
    return False


def gluster_status(logger):
    cmd = "service glusterd status"
    result = process.run(cmd, shell=True, ignore_status=True)
    if not result.exit_status:
        if "active" not in result.stdout or "running" not in result.stdout:
            cmd = "service glusterd start"
            logger.info("Starting glusterd ...")
            result = process.run(cmd, shell=True, ignore_status=True)
            if result.exit_status:
                logger.error("cmd failed: %s" % cmd)
                logger.error("out: %s" % result.stdout)
                return False

    else:
        logger.error("cmd failed: %s." % cmd)
        logger.error("out: %s." % result.stdout)
        return False
    return True


def is_gluster_vol_started(vol_name, logger):
    cmd = "gluster volume info %s" % vol_name
    result = process.run(cmd, shell=True, ignore_status=True)
    vol_status = re.findall(r'Status: (\S+)', result.stdout)
    if 'Started' in vol_status:
        return True
    else:
        return False


def gluster_vol_start(vol_name, logger):
    if not is_gluster_vol_started(vol_name, logger):
        cmd = "gluster volume start %s" % vol_name
        result = process.run(cmd, shell=True, ignore_status=True)
        if result.exit_status:
            logger.error("cmd failed: %s" % cmd)
            logger.error("out: %s" % result.stdout)
            return False

    return True


def gluster_vol_stop(vol_name, logger, force=False):
    if is_gluster_vol_started(vol_name, logger):
        if force:
            cmd = "echo 'y' | gluster volume stop %s force" % vol_name
        else:
            cmd = "echo 'y' | gluster volume stop %s" % vol_name
        result = process.run(cmd, shell=True, ignore_status=True)
        if result.exit_status:
            logger.error("cmd failed: %s" % cmd)
            logger.error("out: %s" % result.stdout)
            return False
    return True


def gluster_vol_delete(vol_name, logger):
    if not is_gluster_vol_started(vol_name, logger):
        cmd = "echo 'y' | gluster volume delete %s" % vol_name
        result = process.run(cmd, shell=True, ignore_status=True)
        if result.exit_status:
            logger.error("cmd failed: %s" % cmd)
            logger.error("out: %s" % result.stdout)
            return False
        return True
    else:
        return False


def is_gluster_vol_avail(vol_name, logger):
    cmd = "gluster volume info"
    result = process.run(cmd, shell=True, ignore_status=True)
    volume_name = re.findall(r'Volume Name: (%s)\n' % vol_name, result.stdout)
    if volume_name:
        return gluster_vol_start(vol_name, logger)


def gluster_vol_create(vol_name, ip, brick_path, logger, force=False):
    if is_gluster_vol_avail(vol_name, logger):
        gluster_vol_stop(vol_name, logger, True)
        gluster_vol_delete(vol_name, logger)

    if force:
        force_opt = "force"
    else:
        force_opt = ""

    cmd = "gluster volume create %s %s:/%s %s" % (vol_name, ip,
                                                  brick_path, force_opt)
    result = process.run(cmd, shell=True, ignore_status=True)
    if result.exit_status:
        logger.error("cmd failed: %s" % cmd)
        logger.error("out: %s" % result.stdout)
        return False

    return is_gluster_vol_avail(vol_name, logger)


def gluster_allow_insecure(vol_name, logger):
    cmd = "gluster volume set %s server.allow-insecure on" % vol_name
    result = process.run(cmd, shell=True, ignore_status=True)
    if result.exit_status:
        logger.error("cmd failed: %s" % cmd)
        logger.error("out: %s" % result.stdout)
        return 1

    cmd = "gluster volume info"
    result = process.run(cmd, shell=True, ignore_status=True)
    if result.exit_status:
        logger.error("cmd failed: %s" % cmd)
        logger.error("out: %s" % result.stdout)
        return 1
    match = re.findall(r'server.allow-inscure: on', result.stdout)
    if not match:
        return 1
    else:
        return 0


def set_fusefs(logger):
    cmd = "setsebool virt_use_fusefs on"
    result = process.run(cmd, shell=True, ignore_status=True)
    if result.exit_status:
        logger.error("cmd failed: %s" % cmd)
        logger.error("out: %s" % result.stdout)
        return 1
    return 0


def setup_gluster(vol_name, ip, brick_path, logger):
    """
    Set up glusterfs environment on localhost
    """
    gluster_status(logger)
    gluster_vol_create(vol_name, ip, brick_path, logger, force=True)
    gluster_allow_insecure(vol_name, logger)
    set_fusefs(logger)
    return 0


def cleanup_gluster(vol_name, logger):
    """
    Clean up glusterfs enviroment on localhost
    """
    gluster_vol_stop(vol_name, logger, True)
    gluster_vol_delete(vol_name, logger)
    return 0


def mount_gluster(vol_name, ip, path, logger):
    cmd = "mount -t glusterfs %s:%s %s" % (ip, vol_name, path)
    result = process.run(cmd, shell=True, ignore_status=True)
    if result.exit_status:
        logger.error("cmd failed: %s" % cmd)
        logger.error("out: %s" % result.stdout)
        return 1
    return 0


def umount_gluster(path, logger):
    cmd = "umount %s" % path
    result = process.run(cmd, shell=True, ignore_status=True)
    if result.exit_status:
        logger.error("cmd failed: %s" % cmd)
        logger.error("out: %s" % result.stdout)
        return 1
    return 0


def setup_nfs(ip, nfspath, mountpath, logger):
    if not os.path.isdir(mountpath):
        logger.info("%s not exist." % mountpath)
        return 1

    cmd = "mount -t nfs %s:%s %s" % (ip, nfspath, mountpath)
    result = process.run(cmd, shell=True, ignore_status=True)
    if result.exit_status:
        logger.error("cmd failed: %s" % cmd)
        logger.error("out: %s" % result.stdout)
        return 1
    return 0


def cleanup_nfs(path, logger):
    cmd = "umount %s" % path
    result = process.run(cmd, shell=True, ignore_status=True)
    if result.exit_status:
        logger.error("cmd failed: %s" % cmd)
        logger.error("out: %s" % result.stdout)
        return 1
    return 0


def iscsi_login(target, portal, logger):
    cmd = "iscsiadm --mode node --login --targetname %s" % target
    cmd += " --portal %s" % portal
    result = process.run(cmd, shell=True, ignore_status=True)
    if result.exit_status:
        logger.error("cmd failed: %s" % cmd)
        logger.error("out: %s" % result.stdout)
    if "successful" in result.stdout:
        return True
    else:
        return False


def iscsi_logout(logger, target=None):
    if target:
        cmd = "iscsiadm --mode node --logout -T %s" % target
    else:
        cmd = "iscsiadm --mode node --logout all"
    result = process.run(cmd, shell=True, ignore_status=True)
    if result.exit_status:
        logger.error("cmd failed: %s" % cmd)
        logger.error("out: %s" % result.stdout)
    if "successful" in result.stdout:
        return True
    else:
        return False


def iscsi_discover(portal, logger):
    cmd = "iscsiadm -m discovery -t sendtargets -p %s" % portal
    result = process.run(cmd, shell=True, ignore_status=True)
    if result.exit_status:
        logger.error("cmd failed: %s" % cmd)
        logger.error("out: %s" % result.stdout)
        return False
    return True


def iscsi_get_sessions(logger):
    cmd = "iscsiadm --mode session"
    result = process.run(cmd, shell=True, ignore_status=True)
    sessions = []
    if "No active sessions" not in result.stdout:
        for session in result.stdout.splitlines():
            ip = session.split()[2].split(',')[0]
            target = session.split()[3]
            sessions.append((ip, target))
    return sessions


def is_login(target, logger):
    sessions = iscsi_get_sessions(logger)
    login = False
    if target in [x[1] for x in sessions]:
        login = True
    return login


def get_device_name(target, logger):
    if is_login(target, logger):
        cmd = "iscsiadm -m session -P 3"
        result = process.run(cmd, shell=True, ignore_status=True)
        if result.exit_status:
            logger.error("cmd failed: %s" % cmd)
            logger.error("out: %s" % result.stdout)
        pattern = r"Target:\s+%s.*?disk\s(\w+)\s+\S+\srunning" % target
        device_name = re.findall(pattern, result.stdout, re.S)
        try:
            device_name = "/dev/%s" % device_name[0]
        except IndexError as err:
            logger.error("Can not find target '%s': %s." % (target, err))
    else:
        logger.error("Session is not logged in yet.")
    return device_name


def create_partition(device, logger):
    timeout = 10
    cmd = "echo -e 'o\\nn\\np\\n1\\n\\n\\nw\\n' | fdisk %s" % device
    result = process.run(cmd, shell=True, ignore_status=True)
    if result.exit_status:
        logger.error("cmd failed: %s" % cmd)
        logger.error("out: %s" % result.stdout)
    while timeout > 0:
        if os.path.exists(device):
            cmd = "dd if=/dev/zero of=%s bs=512 count=10000; sync" % device
            result = process.run(cmd, shell=True, ignore_status=True)
            if result.exit_status:
                logger.error("cmd failed: %s" % cmd)
                logger.error("out: %s" % result.stdout)
            return True
        cmd = "partprobe %s" % device
        result = process.run(cmd, shell=True, ignore_status=True)
        if result.exit_status:
            logger.error("cmd failed: %s" % cmd)
            logger.error("out: %s" % result.stdout)
        time.sleep(1)
        timeout = timeout - 1
    return False


def create_fs(device, logger):
    cmd = "mkfs.ext3 -F %s" % device
    result = process.run(cmd, shell=True, ignore_status=True)
    if result.exit_status:
        logger.error("cmd failed: %s" % cmd)
        logger.error("out: %s" % result.stdout)
        return False
    return True


def mount_iscsi(device, mountpath, logger):
    cmd = "mount %s %s" % (device, mountpath)
    result = process.run(cmd, shell=True, ignore_status=True)
    if result.exit_status:
        logger.error("cmd failed: %s" % cmd)
        logger.error("out: %s" % result.stdout)
        return 1
    return 0


def umount_iscsi(mountpath, logger):
    cmd = "umount %s" % mountpath
    result = process.run(cmd, shell=True, ignore_status=True)
    if result.exit_status:
        logger.error("cmd failed: %s" % cmd)
        logger.error("out: %s" % result.stdout)
        return 1
    return 0


def setup_iscsi(portal, target, mountpath, logger):
    iscsi_discover(portal, logger)
    if not is_login(target, logger):
        iscsi_login(target, portal, logger)
    time.sleep(5)
    device = get_device_name(target, logger)
    create_partition(device, logger)
    create_fs(device, logger)
    if os.path.exists(mountpath):
        mount_iscsi(device, mountpath, logger)
    return 0


def cleanup_iscsi(target, mountpath, logger):
    if is_login(target, logger):
        iscsi_logout(logger, target)
    if os.path.exists(mountpath):
        umount_iscsi(mountpath, logger)
    return 0


def get_env(section, option):
    pwd = os.getcwd()
    envfile = os.path.join(pwd, 'global.cfg')
    envparser = env_parser.Envparser(envfile)
    return envparser.get_value(section, option)


def del_file(path, logger):
    if os.path.exists(path):
        cmd = 'rm -f %s' % (path)
        ret, out = exec_cmd(cmd, shell=True)
        if ret:
            logger.error("delete file failed.")
            logger.error("cmd: %s, out: %s" % (cmd, out))
            return False

    return True


def get_xml_value(dom, path):
    dom_xml = dom.XMLDesc(0)
    tree = lxml.etree.fromstring(dom_xml)
    return tree.xpath(path)


def get_target_hostname(hostname, username, passwd, logger):
    cmd = "hostname"
    ret, out = remote_exec_pexpect(hostname, username, passwd, cmd)
    if ret:
        logger.error("get target hostname failed.")
        return 1

    logger.debug("get_target_hostname: %s" % out)
    return out


def get_image_format(img, logger):
    cmd = "qemu-img info %s | grep 'file format:'" % img
    ret, out = exec_cmd(cmd, shell=True)
    if ret:
        logger.error("cmd: %s, out: %s" % (cmd, out))
        return -1
    return decode_to_text(out[0]).split(":")[1].strip()


def decode_to_text(stream, encoding=locale.getpreferredencoding(),
                   errors='strict'):
    """
    Decode decoding string
    :param stream: string stream
    :param encoding: encode_type
    :param errors: error handling to use while decoding (strict,replace,
                   ignore,...)
    :return: encoding text
    """
    if hasattr(stream, 'decode'):
        return stream.decode(encoding, errors)
    if isinstance(stream, (str, unicode)):
        return stream
    raise TypeError("Unable to decode stream into a string-like type")


def isRelease(version, logger):
    cmd = "cat /etc/redhat-release"
    ret, out = exec_cmd(cmd, shell=True)
    if ret != 0:
        logger.error("cmd: %s, out: %s" % (cmd, out))
        return False
    if "release %s" % version in out[0]:
        return True
    else:
        return False


def get_version():
    cmd = "cat /etc/redhat-release"
    ret, out = exec_cmd(cmd, shell=True)
    if ret != 0:
        return False
    if "Server" in out[0]:
        release = out[0].split(' ')[6]
    else:
        release = out[0].split(' ')[5]
    return release.split('.')


def isPower():
    cmd = "lscpu | grep 'Architecture:'"
    ret, out = exec_cmd(cmd, shell=True)
    if ret != 0:
        return False
    if "ppc" in out[0]:
        return True
    else:
        return False
