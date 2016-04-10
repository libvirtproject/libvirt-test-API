#!/usr/bin/env python
#
# log_generator.py: Generate output log file in XML format.

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

import copy
import shutil
import datetime
from xml.dom import minidom
from xml.dom.minidom import Document
from xml.parsers.expat import ExpatError

import exception


class LogGenerator(object):

    """ Generate and parser log xml file
    """

    def __init__(self, logxml):
        self.logxml = logxml
        self.doc = Document()

    def generate_logxml(self):
        """ generate a new log xml file with head if that doesn't exist """
        XMLFILE = open(self.logxml, "w")
        XMLFILE.write('<?xml version="1.0"?><?xml-stylesheet type="text/xsl"\
                         href="src/log.xsl"?><log xmlns:xlink= \
                         "http://www.w3.org/1999/xlink"></log>')
        XMLFILE.close()

    def repair_logxml(self):
        """ backup currupted log file and generate a new one """
        shutil.move(self.logxml, self.logxml + '.' +
                    str(datetime.datetime.now().strftime("%y%m%d%H%M%S")))
        self.generate_logxml()

    def add_testrun_xml(self, testrunid):
        """ add testrun info into log xml file"""
        try:
            xmldoc = minidom.parse(self.logxml)
        except ExpatError, e:
            # Currupted log xml file, gen a new one.
            self.repair_logxml()
            xmldoc = minidom.parse(self.logxml)
        testrun = self.doc.createElement('testrun')
        testrun.setAttribute("name", testrunid)
        xmldoc.childNodes[1].appendChild(testrun)

        self. __write_to_file(xmldoc, self.logxml)

    def add_test_xml(self, testrunid, testid):
        """ add a test info into log xml file"""
        xmldoc = minidom.parse(self.logxml)
        test = self.doc.createElement('test')
        test.setAttribute("id", testid)
        testrunlist = xmldoc.getElementsByTagName('testrun')
        for testrun in testrunlist:
            runattr = testrun.attributes["name"]
            if runattr.value == testrunid:
                testrun.appendChild(test)

        self.__write_to_file(xmldoc, self.logxml)

    def add_testprocedure_xml(self, testrunid, testid, test_procedure):
        """ add test procedure info into log xml file """
        xmldoc = minidom.parse(self.logxml)

        procedure = self.doc.createElement('test_procedure')
        casename = test_procedure.keys()[0]
        valuedict = test_procedure[casename]

        test_casename = self.doc.createElement('action')
        test_casename.setAttribute('name', casename)

        for arg in valuedict.keys():
            test_arg = self.doc.createElement('arg')
            test_arg.setAttribute("name", arg)
            test_value = self.doc.createTextNode(valuedict[arg])
            test_arg.appendChild(test_value)
            test_casename.appendChild(test_arg)

        procedure.appendChild(test_casename)
        testrunlist = xmldoc.getElementsByTagName('testrun')

        for testrun in testrunlist:
            runattr = testrun.attributes["name"]
            if runattr.value == testrunid:
                testlist = testrun.getElementsByTagName('test')
                for test in testlist:
                    testattr = test.attributes["id"]
                    if testattr.value == testid:
                        test.appendChild(procedure)

        self. __write_to_file(xmldoc, self.logxml)

    def add_test_summary(self, testrunid, testid, result, case_retlist,
                         start_time, end_time, path):
        """ add a test summary xml block into log xml file """
        xmldoc = minidom.parse(self.logxml)
        testresult = self.doc.createElement('result')
        resulttext = self.doc.createTextNode(result)
        testresult.appendChild(resulttext)

        caseresult = self.doc.createElement('caseresult')

        teststarttime = self.doc.createElement('start_time')
        starttimetext = self.doc.createTextNode(start_time)
        teststarttime.appendChild(starttimetext)

        testendtime = self.doc.createElement('end_time')
        endtimetext = self.doc.createTextNode(end_time)
        testendtime.appendChild(endtimetext)

        testpath = self.doc.createElement('path')
        pathtext = self.doc.createTextNode(path)
        testpath.appendChild(pathtext)

        testrunlist = xmldoc.getElementsByTagName('testrun')

        for testrun in testrunlist:
            runattr = testrun.attributes["name"]
            if runattr.value == testrunid:
                testlist = testrun.getElementsByTagName('test')
                for test in testlist:
                    testattr = test.attributes["id"]
                    if testattr.value == testid:
                        test.childNodes.insert(0, testpath)
                        test.childNodes.insert(0, testendtime)
                        test.childNodes.insert(0, teststarttime)
                        test.childNodes.insert(0, testresult)
                        test_cases = test.getElementsByTagName('test_procedure')
                        for i in range(len(test_cases)):
                            retstr = ''
                            if case_retlist[i] == 0:
                                retstr = 'PASS'
                            else:
                                retstr = 'FAIL'
                            itemresult = self.doc.createElement('result')
                            caseresulttext = self.doc.createTextNode(retstr)
                            itemresult.appendChild(caseresulttext)
                            test_cases[i].appendChild(itemresult)

        self. __write_to_file(xmldoc, self.logxml)

    def add_testrun_summary(self, testrunid, passnum, failnum, totalnum,
                            start_time, end_time):
        """ add a testrun summary xml block into log xml file """
        xmldoc = minidom.parse(self.logxml)
        testpass = self.doc.createElement('pass')
        passtext = self.doc.createTextNode(str(passnum))
        testpass.appendChild(passtext)

        testfail = self.doc.createElement('fail')
        failtext = self.doc.createTextNode(str(failnum))
        testfail.appendChild(failtext)

#        testskip = self.doc.createElement('skip')
#        skiptext = self.doc.createTextNode(skipnum)
#        testskip.appendChild(skiptext)

        testtotal = self.doc.createElement('total')
        totaltext = self.doc.createTextNode(str(totalnum))
        testtotal.appendChild(totaltext)

        teststarttime = self.doc.createElement('start_time')
        starttimetext = self.doc.createTextNode(start_time)
        teststarttime.appendChild(starttimetext)

        testendtime = self.doc.createElement('end_time')
        endtimetext = self.doc.createTextNode(end_time)
        testendtime.appendChild(endtimetext)

        testrunlist = xmldoc.getElementsByTagName('testrun')
        for testrun in testrunlist:
            runattr = testrun.attributes["name"]
            if runattr.value == testrunid:
                testrun.childNodes.insert(0, testendtime)
                testrun.childNodes.insert(0, teststarttime)
                testrun.childNodes.insert(0, testtotal)
                testrun.childNodes.insert(0, testfail)
                testrun.childNodes.insert(0, testpass)

        self. __write_to_file(xmldoc, self.logxml)

    def remove_test_xml(self, testrunid, testid):
        """ to remove a test xml block from a log xml file """
        xmldoc = minidom.parse(self.logxml)
        testrunlist = xmldoc.getElementsByTagName('testrun')
        testrunattrlist = []

        for testrun in testrunlist:
            runattr = testrun.attributes["name"]
            if runattr.value == testrunid:
                testrunattrlist.append(runattr.value)
                testlist = testrun.getElementsByTagName('test')
                testattrlist = []
                for test in testlist:
                    testattr = test.attributes["id"]
                    if testattr.value == testid:
                        testattrlist.append(testattr.value)
                        testrun.removeChild(test)
                if len(testattrlist) == 0:
                    raise exception.NoTestFound(
                        "In the xmllog file testrunid %s no testid %s found" %
                        (testrunid, testid))
        if len(testrunattrlist) == 0:
            raise exception.NoTestRunFound(
                "In the xmllog file no testrunid %s found" % testrunid)

        self. __write_to_file(xmldoc, self.logxml)

    def remove_testrun_xml(self, testrunid):
        """ remove a testrun xml block from log xml file """
        xmldoc = minidom.parse(self.logxml)
        testrunlist = xmldoc.getElementsByTagName('testrun')
        testrunattrlist = []

        for testrun in testrunlist:
            runattr = testrun.attributes["name"]
            if runattr.value == testrunid:
                testrunattrlist.append(runattr.value)
                xmldoc.childNodes[1].removeChild(testrun)

        if len(testrunattrlist) == 0:
            raise exception.NoTestRunFound(
                "In the xmllog file no testrunid %s found" % testrunid)

        self. __write_to_file(xmldoc, self.logxml)

    def remove_alltestrun_xml(self):
        """ remove all testrun xml blocks from a log xml file """
        xmldoc = minidom.parse(self.logxml)
        testrunlist = xmldoc.getElementsByTagName('testrun')
        testrunattrlist = []

        for testrun in testrunlist:
            runattr = testrun.attributes["name"]
            testrunattrlist.append(runattr.value)
            xmldoc.childNodes[1].removeChild(testrun)

        self. __write_to_file(xmldoc, self.logxml)
        return testrunattrlist

    def merge_xmlfiles(self, logxml_two):
        """ merge two xmlfiles into one """
        xmldoc_one = minidom.parse(self.logxml)
        xmldoc_two = minidom.parse(logxml_two)
        testrunlist_two = xmldoc_two.getElementsByTagName('testrun')
        testrunlist_two_copy = copy.deepcopy(testrunlist_two)

        for testrun in testrunlist_two_copy:
            xmldoc_one.childNodes[1].appendChild(testrun)

        self. __write_to_file(xmldoc_one, self.logxml)
        self. __write_to_file(xmldoc_two, logxml_two)

    def __write_to_file(self, xmldoc, logxml):
        """ save changes into log xml file """
        file = open(logxml, "w")
        xmldoc.writexml(file)
        file.close()
