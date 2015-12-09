#!/usr/bin/env python
#
# exception.py: Exceptions for the framework.
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


class LibvirtException(Exception):

    code = 200
    message = "General libvirt-test-suite Exception"

    def __init__(self, errorstr=None, code=None):
        self.errorstr = errorstr
        if code:
            self.code = code

    def __str__(self):
        return repr(self.errorstr)

    def response(self):
        self.status = {'code': self.code, ('message': "%s:%s" %
                                           (self.message, str(self)))}
        return self.status


class FileDoesNotExist(LibvirtException):
    code = 201
    message = "File does not exist"


class SectionDoesNotExist(LibvirtException):
    code = 202
    message = "Section in INI file does not exist"


class OptionDoesNotExist(LibvirtException):
    code = 203
    message = "Option in INI file doest not exist"


class SectionExist(LibvirtException):
    code = 204
    message = "Section exists"


class NoTestRunFound(LibvirtException):
    code = 206
    message = "No testrun found in xmllog file"


class NoTestFound(LibvirtException):
    code = 207
    message = "No test found in xmllog file"


class ArgumentsError(LibvirtException):
    code = 208
    message = "Arguments Error"


class FileExist(LibvirtException):
    code = 209
    message = "File exist"


class CaseConfigfileError(LibvirtException):
    code = 210
    message = "Case config file Error"


class MissingVariable(LibvirtException):
    code = 210
    message = "Variables missing from global.cfg [variables] section"


class TestError(LibvirtException):
    code = 211
    message = "Test failed"


class TestCaseError(LibvirtException):
    code = 212
    message = "Testcase Error"
