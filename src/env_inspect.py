#!/usr/bin/env python
#
# env_inspect.py: Check the testing environment.

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

from . import sharedmod

from utils import utils
from utils import process


def check_libvirt(logger):
    virsh = 'virsh -v'
    result = process.run(virsh, shell=True, ignore_status=True)
    if result.exit_status:
        logger.error(result.stdout)
        return 1
    else:
        logger.info("    Virsh command line tool of libvirt: %s" % result.stdout)

    libvirtd = 'libvirtd --version'
    result = process.run(libvirtd, shell=True, ignore_status=True)
    if result.exit_status:
        logger.error(result.stdout)
        return 1
    else:
        logger.info("    %s" % result.stdout)

    default_uri = 'virsh uri'
    result = process.run(default_uri, shell=True, ignore_status=True)
    if result.exit_status:
        logger.error(result.stdout)
        return 1
    else:
        logger.info("    Default URI: %s" % result.stdout.strip())

    if 'qemu' in result.stdout:
        for qemu in ['/usr/bin/qemu-kvm', '/usr/libexec/qemu-kvm', 'kvm']:
            cmd = '%s --version' % qemu
            result = process.run(cmd, shell=True, ignore_status=True)
            if not result.exit_status:
                logger.info("    %s" % result.stdout)
                break
        if result.exit_status:
            logger.error("    no qemu-kvm found")
            return 1
    elif 'xen' in result.stdout:
        #TODO need to get xen hypervisor info here
        pass

    return 0


def hostinfo(logger):
    cmd = 'uname -a'
    result = process.run(cmd, shell=True, ignore_status=True)
    if result.exit_status:
        return 1
    logger.info("    %s" % result.stdout)
    return 0


def sharemod_init(env_parser, logger):
    """ get connection object from libvirt module
        initialize sharemod for use by testcases
    """
    uri = env_parser.get_value('variables', 'defaulturi')
    username = env_parser.get_value('variables', 'username')
    password = env_parser.get_value('variables', 'password')
    conn = utils.get_conn(uri, username, password)
    if not conn:
        return 1

    # initialize conn object in sharedmod
    sharedmod.libvirtobj.clear()
    sharedmod.data.clear()
    sharedmod.libvirtobj['conn'] = conn
    return 0


class EnvInspect(object):

    """to check and collect the testing enviroment infomation
       before performing testing
    """

    def __init__(self, env_parser, logger):
        self.logger = logger
        self.env_parser = env_parser

    def env_checking(self):
        if hostinfo(self.logger):
            return 1

        if check_libvirt(self.logger):
            return 1

        if sharemod_init(self.env_parser, self.logger):
            return 1

        return 0

    def close_hypervisor_connection(self):
        conn = sharedmod.libvirtobj.get('conn', None)
        if conn:
            # conn probably is invalid pointer
            # that means the connection is closed
            # If so we ignore the error here
            try:
                conn.close()
                conn = None
            except Exception as err:
                pass

        sharedmod.libvirtobj.clear()
        sharedmod.data.clear()
        return 0
