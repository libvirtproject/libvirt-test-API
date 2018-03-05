#!/usr/bin/env python
#
# process.py: Multiple process module
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
import sys


class Process:

    def __init__(self, list):
        self.procs = list
        self.pids = []

    def fork(self):
        for i in self.procs:
            pid = os.fork()
            if 0 == pid:
                ret = i()
                os._exit(ret)
            elif 0 < pid:
                self.pids.append(pid)
            else:
                print("ERROR: Failed on forking process")
                sys.exit(1)

    def wait(self):
        passnum = 0
        failnum = 0
        for i in self.pids:
            pid, ret = os.waitpid(i, 0)

            if ret:
                failnum += 1
            else:
                passnum += 1
        return passnum, failnum
