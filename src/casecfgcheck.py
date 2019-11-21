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


class CaseCfgCheck(object):

    """validate the options in testcase config file"""

    def __init__(self, proxy_obj, activities_list):
        # XXX to check the first testcase list in activities_list
        self.activity = activities_list[0]

        self.case_params = proxy_obj.get_params_variables()

    def check(self):
        """check options to each testcase in case config file"""
        case_number = 0
        error_flag = 0
        passed_testcase = []
        for testcase in self.activity:
            if testcase in passed_testcase:
                continue

            testcase_name = list(testcase.keys())[0]
            if testcase_name == 'clean' or \
               testcase_name == 'sleep':
                continue

            actual_params = list(testcase.values())[0]
            required_params, optional_params = self.case_params[testcase_name]

            case_number += 1
            ret = self._check_params(required_params, optional_params, actual_params)
            if ret:
                error_flag = 1
                print("the No.%s : %s\n" % (case_number, testcase_name))

            passed_testcase.append(testcase)

        if error_flag:
            return 1
        return 0

    def _check_params(self, required_params, optional_params, actual_params):
        for p in required_params:
            if p not in list(actual_params.keys()):
                print("Parameter %s is required" % p)
                return 1

        for p in list(actual_params.keys()):
            if p not in required_params and p not in optional_params:
                print("Unknown parameter '%s'" % p)
                return 1

        return 0
