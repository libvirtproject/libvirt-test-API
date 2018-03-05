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


class Filter(object):

    """filter activity list to form various data list"""

    def __init__(self, activities_list):
        self.testcase_keys = []
        for activity in activities_list:
            for testcase in activity:
                testcases_key = list(testcase.keys())
                self.testcase_keys += testcases_key

    def unique_testcase_cleansuffix(self):
        """get a list of module:testcase from activities_list
           eliminate duplicate items, with 'module:testcase_clean'
        """
        keylist_clean = self._keylist_cleanappended_without_sleep()
        return list(set(keylist_clean))

    def unique_testcases(self):
        """ get a list of module:testcase from activities_list
            eliminate duplicate items
        """
        keylist = self._keylist_without_sleep_clean()
        return list(set(keylist))

    def _keylist_without_sleep_clean(self):
        """ filter out 'clean' and 'sleep' flag
            to generate a list of testcases
        """
        keylist = []
        for key in self.testcase_keys:
            if key == 'clean' or key == 'sleep':
                continue

            keylist.append(key)

        return keylist

    def _keylist_cleanappended_without_sleep(self):
        """ remove 'sleep' flag, and append ':_clean' to
            the previous testcase to form a new element
        """
        keylist_clean = []
        prev_casename = ''

        for key in self.testcase_keys:
            if key == 'sleep':
                continue

            if key == 'clean':
                keylist_clean.append(prev_casename + ":_clean")
                continue

            prev_casename = key
            keylist_clean.append(prev_casename)

        return keylist_clean
