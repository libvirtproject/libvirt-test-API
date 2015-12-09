#!/usr/bin/env python
# Filename: virtlab.py
# Summary: Writing test logs and case generator for virtlab.
# Description: This module is for test logs and case generation use.
# Maintainer: nzhang@redhat.com, xhu@redhat.com
# Updated: Thu Apr 1, 2010
# Version: 0.1.0

import os
import sys
import re
import shutil
import commands
from optparse import OptionParser

import utils

guest = {}
guest['rhel3u9'] = 'RHEL-3.9'
guest['rhel4u8'] = 'RHEL-4.8'
guest['rhel5u4'] = 'RHEL-Server-5.4'
guest['rhel5u5'] = 'RHEL-Server-5.5'
guest['rhel6'] = 'RHEL-6.0'
guest['fedora12'] = 'Fedora-12'
guest['winxp'] = 'WinXP'
guest['win2003'] = 'Win2003'
guest['win2008'] = 'Win2008'
guest['win2008r2'] = 'Win2008R2'
guest['win7'] = 'Win7'

memory = {}
memory['1048576'] = '1G'
memory['2097152'] = '2G'
memory['4194304'] = '4G'
memory['8388608'] = '8G'
memory['1G'] = '1048576'
memory['2G'] = '2097152'
memory['4G'] = '4194304'
memory['8G'] = '8388608'

test_run_params = {}


def result_log(mod_case_func, case_params, ret, case_start_time, case_end_time):
    # get test run parameters
    global test_run_params
    libvirt_ver = utils.get_libvirt_version()
    hypervisor_ver = utils.get_hypervisor_version()
    kernel_ver = utils.get_host_kernel_version()

    testcase = mod_case_func
    if ret == 0:
        status = 'GOOD'
    else:
        status = 'FAIL'

    line = '-' * 120 + "\nSTART\t[%s][][libvirt_version=%s][hypervisor_version=%s][kernel_version=%s]" % (testcase, libvirt_ver, hypervisor_ver, kernel_ver)
    for key in case_params.keys():
        if key != "xml":
            line += "[%s=%s]" % (key, case_params[key])
    line += "\t%s\n%s\nEND\t%s" % (case_start_time, status, case_end_time)
    logfile = 'result/result.log'
    if os.path.isfile(logfile):
        try:
            fp = open(logfile, 'a+')
            line = '\n' + line
            fp.writelines(line)
            fp.close()
        except:
            print "ERROR: error writing to file '" + logfile + "'!"
            return False
    else:
        try:
            if os.path.exists('result'):
                pass
            else:
                os.makedirs('result')
            fp = open(logfile, 'w+')
            line = '\n' + line
            fp.writelines(line)
            fp.close()
        except:
            print "ERROR: error writing to file '" + logfile + "'!"
            return False
    return True


def case_spawn(filename, str1, str2):
    fp_read = open(filename, 'r')
    filer = fp_read.read()
    sub = re.sub(str1, str2, filer)
    fp_read.close()
    fp_write = open(filename, 'w')
    fp_write.write(sub)
    fp_write.close()


def isvirtlab():
    cmd = "ps aux | grep STAFProc |grep -v grep"
    stat, ret = commands.getstatusoutput(cmd)
    if stat == 0 and ret != '':
        return True
    else:
        return False


def create_virtlab_log(testrunid):
    create_virtlab_cmd = 'cp -Rf log/%s result' % testrunid
    os.system(create_virtlab_cmd)
