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
#
# This module matches the reference of clearing function from each testcase
# to the corresponding testcase's argument in the order of testcase running

from utils import log

from . import mapper


class EnvClear(object):

    """ Generate a callable class of executing clearing function in
        each testcase.
    """

    def __init__(self, cases_clearfunc_ref_dict, activity, logfile, loglevel):
        self.cases_clearfunc_ref_dict = cases_clearfunc_ref_dict
        self.logfile = logfile
        self.loglevel = loglevel

        mapper_obj = mapper.Mapper(activity)
        mod_casename_func = mapper_obj.module_casename_func_noflag()

        self.case_name_list = []
        for case in mod_casename_func:
            mod_case_func = list(case.keys())[0]
            self.case_name_list.append(mod_case_func)

        self.case_params_list = []
        for case in mod_casename_func:
            case_params = list(case.values())[0]
            self.case_params_list.append(case_params)

    def __call__(self):
        retflag = self.env_clear()
        return retflag

    def env_clear(self):
        """ Run each clean function with the corresponding arguments """

        envlog = log.EnvLog(self.logfile, self.loglevel)
        logger = envlog.env_log()

        testcase_number = len(self.case_name_list)

        for i in range(testcase_number):

            mod_case_func = self.case_name_list[i]
            case_params = self.case_params_list[i]

            case_params['logger'] = logger
            if mod_case_func in self.cases_clearfunc_ref_dict:
                self.cases_clearfunc_ref_dict[mod_case_func](case_params)

        return 0
