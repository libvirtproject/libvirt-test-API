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
# This module is for configuration file parsing, to generate a case list.

import re
import os
import sys
import copy
import string

from . import exception
from . import env_parser

from six.moves import xrange as range


class CaseFileParser(object):

    """ Parser the case configuration file to generate a data list.
    """

    def __init__(self, casefile=None, debug=False):
        self.list = [[]]
        self.variables = {}
        self.missing_variables = []
        self.debug = debug
        self.casefile = casefile
        self.env = env_parser.Envparser("global.cfg")
        self.loop_finish = False
        self.loop_start = 0
        self.loop_end = 0
        self.loop_times = 0
        self.loop_list = []

        if casefile:
            self.parse_file(casefile)

    def set_debug(self, debug=False):
        """ Enable or disable debugging support. """
        self.debug = debug

    def parse_file(self, casefile):
        """ Open casefile for parsering. """
        if not os.path.exists(casefile):
            raise exception.FileDoesNotExist(
                "Config file: %s not found" % casefile)
        self.casefile = casefile
        with open(casefile, "r") as fh:
            self.list = self.parse(fh, self.list)
        return self.list

    def get_list(self):
        """ Return the list of dictionaries.
        """
        return self.list

    def get_next_line(self, fh):
        """ Get the next non-empty, non-comment line in file.
            If no line is available, return None.
        """
        comment_flag = 0
        while True:
            line = fh.readline()
            if line == '':
                if comment_flag == 1:
                    raise exception.CaseConfigfileError(
                        "File ended before a comment block is closed!")
                return None

            stripped_line = line.strip()
            if len(stripped_line) == 0:
                continue
            elif stripped_line.startswith('/*'):
                if comment_flag == 0:
                    comment_flag = 1
                    continue
                raise exception.CaseConfigfileError("comments delimiter mismatch!")
            elif stripped_line.endswith('*/'):
                if comment_flag == 1:
                    comment_flag = 0
                    continue
                raise exception.CaseConfigfileError("comments delimiter mismatch!")
            else:
                if stripped_line.startswith('*/'):
                    raise exception.CaseConfigfileError(
                        "For proper indent, '*/' must be at the end of a line!")
                if stripped_line.endswith('/*'):
                    raise exception.CaseConfigfileError(
                        "For proper indent, '/*' must be at the beginning of a line!")
                if re.match(r'(#|//).*', stripped_line) or comment_flag:
                    continue

                return line

    def get_next_line_indent(self, fh):
        """ Return the indent level of the next non-empty,
            non-comment line in file.If no line is available, return -1.
        """
        pos = fh.tell()
        line = self.get_next_line(fh)
        if not line:
            fh.seek(pos)
            return -1
        line = line.expandtabs()
        indent = 0
        while line[indent] == ' ':
            indent += 1
        fh.seek(pos)
        return indent

    def add_option_value(self, caselist, casename, option, value):
        """ Add option to the data list. """
        dictionary = caselist[-1]
        testkey = list(dictionary.keys())[0]
        if casename == testkey:
            if option not in dictionary[testkey]:
                dictionary[testkey][option] = value

    def debug_print(self, str1, str2=""):
        """Nicely print two strings and an arrow.  For internal use."""
        if self.debug:
            if str2:
                str = "%-50s ---> %s" % (str1, str2)
            else:
                str = str1
            print(str)

    def variables_lookup(self, values):
        res = []
        for val in values:
            if len(val) != 0 and val[0] == '$':
                varname = val[1:]
                self.debug_print("found variable %s" % varname)
                try:
                    value = self.env.get_value("variables", varname)
                    value = string.strip(value)
                    self.variables[varname] = value
                    if value == "":
                        self.debug_print("variable %s is empty" % varname)
                        self.missing_variables.append(varname)
                    else:
                        res.append(value)
                except exception.OptionDoesNotExist as e:
                    self.missing_variables.append(varname)
                except exception.SectionDoesNotExist as e:
                    self.missing_variables.append(varname)
                except:
                    self.missing_variables.append(varname)
            else:
                res.append(val)
        return res

    def format_string_parse(self, string):
        """
        For parsing formatted strings.
        This functoin split string, and return a list.
        String are splited by space, but quotated part won't be splited.

        Example:
            plain string: value => ['value']
            empty string: '' => ['']
            string with space: 'word1 word2' word3 => ['word1 word2', 'word3']
            string with escaped quatatoin: libvirt\'s test => ['libvirt\'s', test]
            string with diffrent quatatoin: "libvirt's", test => ['"libvirt\'s"', test]

        The quotation format is basically the same python
        """

        string = iter(string)
        quota_stack = []
        value_list = []
        value = ""
        for char in string:
            if char == "\\":
                try:
                    next_char = next(string)
                    if next_char in ['"', "'", "\\"]:
                        value += next_char
                    elif next_char == 'x':
                        u_prefix = "\\x"
                        for i in range(2):
                            u_prefix += next(string)
                        value += u_prefix.decode('unicode-escape')
                    elif next_char == 'u':
                        u_prefix = "\\u"
                        for i in range(4):
                            u_prefix += next(string)
                        value += u_prefix.decode('unicode-escape')
                except StopIteration:
                    raise exception.CaseConfigfileError(
                        "Escape character at end of line.")
            elif char in ["'", '"']:
                if len(quota_stack) != 0:
                    if char == quota_stack[-1]:
                        quota_stack.pop()
                        value_list.append(value)
                        value = ""
                    else:
                        value += char
                else:
                    quota_stack.append(char)
            elif char == " ":
                if len(quota_stack) != 0:
                    value += str(char)
                elif value != "":
                    value_list.append(value)
                    value = ""
            else:
                value += char
        if len(quota_stack) != 0:
            raise exception.CaseConfigfileError("Quotation not ending!")
        if value != "":
            value_list.append(value)
        return value_list

    def option_parse(self, fh, list, casename):
        """ For options of a case parsing. """
        new_list = []

        optionname = self.get_next_line(fh)
        tripped_optionname = optionname.strip()

        indent = self.get_next_line_indent(fh)
        if indent == 0:
            raise exception.CaseConfigfileError("case indentation error!")
        elif indent == 4:
            raise exception.CaseConfigfileError("case indentation error!")
        elif indent == -1:
            raise exception.CaseConfigfileError("option without value error!")
        else:
            pass

        self.debug_print("the option name is", tripped_optionname)

        while True:
            temp_list = []

            indent = self.get_next_line_indent(fh)
            if indent == -1:
                break

            for caselist in list:
                new_dict = copy.deepcopy(caselist)
                temp_list.append(new_dict)

            if indent == 0:
                new_list = self.parse(fh, new_list)
                return new_list
            elif indent == 4:
                new_list = self.option_parse(fh, new_list, casename)
                return new_list
            elif indent == 8:
                valuestring = self.get_next_line(fh)

                # Split valuestring
                tripped_valuelist = self.format_string_parse(valuestring.strip())
                # look for variable and try to substitute them
                tripped_valuelist = self.variables_lookup(tripped_valuelist)
                if len(self.missing_variables) != 0:
                    raise exception.MissingVariable(
                        "The variables %s referenced in %s could not be found in global.cfg" %
                        (self.missing_variables, self.casefile))

                tripped_valuename = tripped_valuelist[0]

                self.debug_print("the option_value we are parsing is", tripped_valuename)
                self.debug_print("the temp_list is", temp_list)

                filterter_list = []

                for caselist in temp_list:
                    self.debug_print("before parsing, the caselist is", caselist)

                    if len(tripped_valuelist) > 1:
                        if (tripped_valuelist[1] == "only" and
                                len(tripped_valuelist) == 3):
                            self.debug_print("the value with a keywords which is",
                                             tripped_valuelist[1])

                            filterters = tripped_valuelist[2].split("|")
                            for filterter in filterters:
                                self.debug_print("the filterter we will filt the"
                                                 " temp_list is", filterter)

                                if re.findall(filterter.encode('unicode-escape'), str(caselist)):
                                    self.add_option_value(
                                        caselist,
                                        casename,
                                        tripped_optionname,
                                        tripped_valuename)
                                    break
                            else:
                                filterter_list.append(caselist)
                        elif (tripped_valuelist[1] == "no" and
                              len(tripped_valuelist) == 2):
                            self.debug_print(
                                "the value with a keywords which is", tripped_valuelist[1])

                            if re.findall(tripped_valuename.encode('unicode-escape'),
                                          str(caselist)):
                                temp_list = [case for case in caselist if casename in case]
                        elif (tripped_valuelist[1] == "no" and
                              len(tripped_valuelist) == 3):
                            filterters = tripped_valuelist[2].split("|")
                            for filterter in filterters:
                                if re.findall(filterter.encode('unicode-escape'), str(caselist)):
                                    filterter_list.append(caselist)
                                    break
                            else:
                                self.add_option_value(caselist, casename,
                                                      tripped_optionname,
                                                      tripped_valuename)
                        elif (tripped_valuelist[1] == "include" and
                              len(tripped_valuelist) == 2):
                            if re.findall(tripped_valuename.encode('unicode-escape'),
                                          str(caselist)):
                                self.add_option_value(caselist,
                                                      casename,
                                                      tripped_optionname,
                                                      tripped_valuename)
                                temp_list = [caselist]
                    else:
                        self.add_option_value(caselist,
                                              casename,
                                              tripped_optionname,
                                              tripped_valuename)

                    self.debug_print("after parsing the caselist is", caselist)

                trash = [temp_list.remove(i) for i in filterter_list]

                self.debug_print("after handling the temp_list is", temp_list)

                new_list += temp_list
            else:
                raise exception.CaseConfigfileError("value indentation error!")

        return new_list

    def parse(self, fh, list):
        """ For the testcase name parsing. """

        tripped_casename = ''
        while True:
            self.debug_print("the list is", list)

            indent = self.get_next_line_indent(fh)
            tripped_casename = ""
            if indent < 0:
                break
            elif indent == 0:
                casestring = self.get_next_line(fh)

                tripped_caselist = casestring.strip().split()
                tripped_casename = tripped_caselist[0]

                self.debug_print("we begin to handle the case", tripped_casename)

                if self.loop_finish:
                    for i in range(len(list)):
                        self.loop_list.append([])

                    i = 0
                    for caselist in list:
                        for j in range(self.loop_start, self.loop_end):
                            self.loop_list[i].append(caselist.pop())

                        self.loop_list[i].reverse()
                        self.debug_print("loop_list is", self.loop_list)
                        caselist.extend(self.loop_list[i] * self.loop_times)
                        i += 1

                    self.loop_finish = False
                    self.loop_list = []

                if len(tripped_caselist) == 2 and \
                        tripped_caselist[1] == "start_loop":
                    for caselist in list:
                        newdict = {}
                        newdict[tripped_casename] = {}
                        caselist.append(newdict)
                        self.loop_start = len(caselist) - 1
                    continue

                if len(tripped_caselist) == 3 and \
                        tripped_caselist[1] == "end_loop":
                    looptimes = tripped_caselist[2]
                    self.debug_print("looptimes is", looptimes)
                    self.loop_times = int(looptimes)
                    self.loop_finish = True
                    for caselist in list:
                        newdict = {}
                        newdict[tripped_casename] = {}
                        caselist.append(newdict)
                        self.loop_end = len(caselist)
                    continue

                if len(tripped_caselist) == 3 and \
                        tripped_caselist[1] == "times":
                    times = tripped_caselist[2]

                    self.debug_print(
                        "the case with a keywords which is %s \
                         keywords_value is %s" %
                        (tripped_caselist[1], times))

                    for i in range(int(times)):
                        for caselist in list:
                            newdict = {}
                            newdict[tripped_casename] = {}
                            caselist.append(newdict)

                if len(tripped_caselist) == 2 and \
                        tripped_casename == "sleep":
                    sleepsecs = tripped_caselist[1]
                    for caselist in list:
                        newdict = {}
                        newdict[tripped_casename] = {'sleep': sleepsecs}
                        caselist.append(newdict)
                    continue

                if len(tripped_caselist) == 1 and \
                        tripped_casename == "clean":
                    cleanflag = 'yes'
                    for caselist in list:
                        newdict = {}
                        newdict[tripped_casename] = {'clean': cleanflag}
                        caselist.append(newdict)
                    continue

                if tripped_casename == "options":
                    option_case = [{'options': {}}]
                    option_list = tripped_caselist[1:]
                    for option in option_list:
                        (optionkey, optionvalue) = option.split("=")
                        option_case[0]['options'][optionkey] = optionvalue
                    list.append(option_case)
                    continue

                if not re.match(".+:.+", tripped_casename):
                    raise exception.CaseConfigfileError(
                        "%s line format error!" % tripped_casename)

                for caselist in list:
                    newdict = {}
                    newdict[tripped_casename] = {}
                    caselist.append(newdict)
            elif indent > 0:
                if indent == 4:
                    self.debug_print("we begin to parse the option line")
                    list = self.option_parse(fh, list, tripped_casename)
                else:
                    raise exception.CaseConfigfileError("option indentation error!")
        return list

if __name__ == "__main__":

    if len(sys.argv) >= 2:
        casefile = sys.argv[1]
    else:
        print("No config file is given, use the default case.conf\n")
        casefile = os.path.join(os.path.dirname(sys.argv[0]), "case.conf")
    try:
        list = CaseFileParser(casefile, debug=True).get_list()
        print("The number of generated list is %s" % len(list))
        print(list)
    except Exception as e:
        print(e)
