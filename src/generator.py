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
# This module to initilize log module and match testcase function from
# proxy with corresponding argument to form a callable function.

import time
import fcntl
import sys
import traceback

from utils import log
from utils import virtlab

from . import mapper
from .testcasexml import xml_file_to_str
from . import env_parser
from . import env_inspect
from . import format

# for virtlab
if virtlab.isvirtlab():
    VirtLabFlag = True
else:
    VirtLabFlag = False


class FuncGen(object):

    """ To generate a callable testcase"""

    def __init__(self, cases_func_ref_dict,
                 cases_checkfunc_ref_dict,
                 proxy_obj,
                 activity, logfile,
                 testrunid, testid,
                 log_xml_parser, lockfile,
                 loglevel):
        self.cases_func_ref_dict = cases_func_ref_dict
        self.cases_checkfunc_ref_dict = cases_checkfunc_ref_dict
        self.proxy_obj = proxy_obj
        self.logfile = logfile
        self.testrunid = testrunid
        self.testid = testid
        self.lockfile = lockfile
        self.loglevel = loglevel

        self.fmt = format.Format(logfile)
        self.log_xml_parser = log_xml_parser

        # Save case information to a file in a format
        self.__case_info_save(activity, testrunid)

        self.env = env_parser.Envparser("global.cfg")

        mapper_obj = mapper.Mapper(activity)
        case_list = mapper_obj.module_casename_func_map()

        for test_procedure in case_list:
            log_xml_parser.add_testprocedure_xml(testrunid,
                                                 testid,
                                                 test_procedure)
        self.case_name_list = []
        for case in case_list:
            mod_case_func = list(case.keys())[0]
            self.case_name_list.append(mod_case_func)

        self.case_params_list = []
        for case in case_list:
            case_params = list(case.values())[0]
            self.case_params_list.append(case_params)

    def __call__(self):
        retflag = self.generator()
        return retflag

    def generator(self):
        """ Run each test case with the corresponding arguments and
            add log object into the dictionary of arguments
        """

        envlog = log.EnvLog(self.logfile, self.loglevel)
        env_logger = envlog.env_log()
        casenumber = len(self.case_name_list)
        start_time = time.strftime("%Y-%m-%d %H:%M:%S")
        env_logger.info("Checking Testing Environment... ")
        envck = env_inspect.EnvInspect(self.env, env_logger)

        if envck.env_checking() == 1:
            sys.exit(1)
        else:
            env_logger.info("\nStart Testing:")
            env_logger.info("    Case Count: %s" % casenumber)
            env_logger.info("    Log File: %s\n" % self.logfile)

        caselog = log.CaseLog(self.logfile, self.loglevel)
        case_logger = caselog.case_log()

        # retflag: [pass, fail, skip]
        retflag = [0, 0, 0]
        case_retlist = []
        for i in range(casenumber):

            clean_flag = False

            mod_case_func = self.case_name_list[i]
            if mod_case_func.endswith(':clean'):
                mod_case_func = mod_case_func[:-6]
                clean_flag = True

            mod_case = mod_case_func.rsplit(":", 1)[0]
            self.fmt.print_start(mod_case, env_logger)

            case_params = {k: v
                           for k, v in list(self.case_params_list[i].items())}
            case_params['logger'] = case_logger

            if mod_case_func in self.cases_checkfunc_ref_dict:
                if self.cases_checkfunc_ref_dict[mod_case_func](case_params):
                    case_logger.info("Failed to meet testing requirement")
                    self.fmt.print_end(mod_case, 2, env_logger)
                    retflag[2] += 1
                    continue

            case_start_time = time.strftime("%Y-%m-%d %H:%M:%S")

            ret = 1
            try:
                try:
                    if mod_case_func == 'sleep':
                        sleepsecs = case_params.get('sleep', 0)
                        case_logger.info("sleep %s seconds" % sleepsecs)
                        time.sleep(int(sleepsecs))
                        ret = 0
                    else:
                        xml_file_to_str(self.proxy_obj, mod_case, case_params)

                        ret = self.cases_func_ref_dict[
                            mod_case_func](case_params)
                        # In the case where testcase return -1 on error
                        if ret < 0:
                            ret = 1

                        if clean_flag:
                            # Pass return flag to cleanup function.
                            case_params['ret_flag'] = ret
                            clean_func = mod_case_func + '_clean'
                            self.fmt.print_string(12*" " + "Cleaning...\n", env_logger)
                            # the return value of clean function is optional
                            clean_ret = self.cases_func_ref_dict[
                                clean_func](case_params)
                            if clean_ret and clean_ret == 1:
                                self.fmt.print_string(21*" " + "Fail\n", env_logger)
                                continue

                            self.fmt.print_string(21*" " + "Done\n", env_logger)
                except Exception as e:
                    case_logger.error(traceback.format_exc())
                    continue
            finally:
                case_end_time = time.strftime("%Y-%m-%d %H:%M:%S")
                if ret == 0:
                    retflag[0] += 1
                elif ret == 1:
                    retflag[1] += 1
                elif ret == 2:
                    retflag[2] += 1

                self.fmt.print_end(mod_case, ret, env_logger)

                # for virtlab
                if VirtLabFlag:
                    virtlab.result_log(mod_case_func, case_params, ret, case_start_time, case_end_time)

                case_retlist.append(ret)
        # close hypervisor connection
        envck.close_hypervisor_connection()
        end_time = time.strftime("%Y-%m-%d %H:%M:%S")

        env_logger.info("\nSummary:")
        env_logger.info("    Total:%s [Pass:%s Fail:%s Skip:%s]" %
                        (casenumber, retflag[0], retflag[1], retflag[2]))

        result = (retflag[1] and "FAIL") or "PASS"

        # for virtlab
        if VirtLabFlag:
            virtlab.create_virtlab_log(self.testrunid)

        fcntl.lockf(self.lockfile.fileno(), fcntl.LOCK_EX)
        self.log_xml_parser.add_test_summary(self.testrunid,
                                             self.testid,
                                             result,
                                             case_retlist,
                                             start_time,
                                             end_time,
                                             self.logfile)
        fcntl.lockf(self.lockfile.fileno(), fcntl.LOCK_UN)
        return retflag[1]

    def __case_info_save(self, case, testrunid):
        """ Save data of each test into a file under the testrunid directory
            which the test belongs to.
        """
        caseinfo_file = "log" + "/" + str(testrunid) + "/" + "caseinfo"
        CASEINFO = open(caseinfo_file, "a")
        CASEINFO.write(str(case) + "\n")
        CASEINFO.close()
