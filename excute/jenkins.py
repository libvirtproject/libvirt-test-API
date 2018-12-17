#!/usr/bin/python

##@ Filename: virtlab.py
##@ Summary: This is libvirt-test-API interface for virtlab.
##@ Description: This module is for libvirt-test-API interface.
#Because the libvirt-test-API dir name is changed to jenkins
#project name in build path, so use libvirt-test-API-rhel7 as
#project name,This is a workaround for the moment.

import os
import sys
import re
import shutil
import subprocess


def append_path(path):
    """Append root path of package"""
    if path in sys.path:
        pass
    else:
        sys.path.append(path)


pwd = os.getcwd()
result = re.search('(.*)libvirt-test-API', pwd)
homepath = result.group(0)
append_path(homepath)

from utils import virtlab

if __name__ == "__main__":

    # Parse parameters passed by virtlab
    memory = {}
    memory['1048576'] = '1G'
    memory['2097152'] = '2G'
    memory['4194304'] = '4G'
    memory['8388608'] = '8G'
    memory['1G'] = '1048576'
    memory['2G'] = '2097152'
    memory['4G'] = '4194304'
    memory['8G'] = '8388608'

    options = sys.argv[1:]
    vardict = {}
    srcdir = 'templates/'
    targetfile = 'case.conf'

    for option in options:
        result = re.search('--(.*)=(.*)', option)
        if result:
            varname = result.group(1)
            varvalue = result.group(2)
            print "%s : %s" % (varname, varvalue)
            if varname == 'confile':
                srcfile = varvalue
            elif varname == 'memory':
                vardict[varname] = memory[varvalue]
            else:
                vardict[varname] = varvalue
        else:
            print "unknown option type"
            sys.exit(1)

    # Generate case.conf by replace variables in template conf
    shutil.copy('%s%s' % (srcdir, srcfile), targetfile)

    for key in vardict.keys():
        virtlab.case_spawn(targetfile, '#%s#' % key.upper(), vardict[key])

#    (status, text) = commands.getstatusoutput('setenforce 0')
    retcode = subprocess.call(["python", "libvirt-test-api"])
