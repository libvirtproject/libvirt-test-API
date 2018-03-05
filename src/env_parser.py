#!/usr/bin/env python
#
# env_parser.py: Parser for environment config (global.cfg).
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

try:
    import ConfigParser
except ImportError:
    import configparser as ConfigParser

import os

from . import exception


class Envparser(object):

    def __init__(self, configfile):
        self.cfg = ConfigParser.ConfigParser()
        if os.path.isfile(configfile):
            self.cfg.read(configfile)
        else:
            raise exception.FileDoesNotExist(
                "global.cfg is not a regular file or nonexist")

    def has_section(self, section):
        if self.cfg.has_section(section):
            return True
        else:
            return False

    def has_option(self, section, option):
        if self.has_section(section):
            if self.cfg.has_option(section, option):
                return True
            else:
                return False
        else:
            raise exception.SectionDoesNotExist(
                "In global.cfg, the section %s is nonexist" % section)

    def sections_list(self):
        return self.cfg.sections()

    def options_list(self, section):
        if self.has_section:
            return self.cfg.options(section)
        else:
            raise exception.SectionDoesNotExist(
                "In global.cfg, the section %s is nonexist" % section)

    def get_value(self, section, option):
        if self.has_section:
            if self.has_option:
                return self.cfg.get(section, option)
            else:
                raise exception.OptionDoesNotExist(
                    "In global.cfg, the option %s is nonexist" % option)
        else:
            raise exception.SectionDoesNotExist(
                "In global.cfg, the section %s is nonexist" % section)

    def get_items(self, section):
        if self.has_section:
            return self.cfg.items(section)
        else:
            raise exception.SectionDoesNotExist(
                "In global.cfg, the section %s is nonexist" % section)

    def add_section(self, section):
        if self.has_section:
            raise exception.SectionExist(
                "Section %s exists already" % section)
        else:
            self.cfg.add_section(section)
            return True

    def remove_option(self, section, option):
        if self.has_section:
            if self.has_option:
                self.cfg.remove_option(section, option)
                return True
            else:
                raise exception.OptionDoesNotExist(
                    "In global.cfg, the option %s is nonexist" % option)
        else:
            raise exception.SectionDoesNotExist(
                "In global.cfg, the section %s is nonexist" % section)

    def remove_section(self, section):
        if self.has_section:
            self.cfg.remove_section(section)
            return True
        else:
            raise exception.SectionDoesNotExist(
                "In global.cfg, the section %s is nonexist" % section)

    def set_value(self, section, option, value):
        if self.has_section:
            if self.has_option:
                self.cfg.set(section, option, value)
                return True
            else:
                raise exception.OptionDoesNotExist(
                    "In global.cfg, the option %s is nonexist" % option)
        raise exception.SectionDoesNotExist(
            "In global.cfg, the section %s is nonexist" % section)
