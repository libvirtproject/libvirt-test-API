#!/usr/bin/env python
#
# xml_parser.py: Parse XML document, the result is a python dict.
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
from xml.dom import minidom

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class xml_parser(object):

    """Class xml_parser. It parses and xml document into a python dictionary.
       The elements of the xml documents will be python dictionary keys. For
       example, the xml document:
          <firstel>firstdata</firstel>
          <secondel>
              <subinsecond> seconddata </subinsecond>
          </secondel>
       will be parsed into the python dictionary:
         { "firstel":"firstdata" , "secondel":{"subsinsecond":"seconddata"} }
       Then the data can be retrieve as:
       out = xml_parser.xml_parser().parse(xml)
       out["firstel"] (this will be firstdata )
       out["secondel"]["subinsecond"] (this will be seconddata)

       attributes will be put into attr hash, so say the xml document is:
       <source>
         <device path = '/dev/mapper/vg_hpdl120g501-lv_home'/>
       </source>

       It will be parsed into:
       out["source"]["device"]["attr"]["path"]
       which will be set to:
         "/dev/mapper/vg_hpdl120g501-lv_home"
    """

    def __init__(self):
        pass

    def parse(self, arg):
        out = None
        if isinstance(arg, file):
            out = self.parsefile(arg)
        elif os.path.exists(arg):
            print("file: %s " % arg)
            out = self.parsefile(arg)
        else:
            streamstr = StringIO(arg)
            out = self.parsefile(streamstr)
        if out is not None:
            return out

    def parsefile(self, filepath):
        xmldoc = minidom.parse(filepath)
        thenode = xmldoc.firstChild
        outdic = dict()
        self.parseintodict(thenode, 0, outdic)
        return outdic

    def parseintodict(self, node, level, out, rootkey=None):
        for thenode in node.childNodes:
            if thenode.nodeType == node.ELEMENT_NODE:
                key = thenode.nodeName
                value = None
                try:
                    value = thenode.childNodes[0].data
                    if value.strip() == '':
                        value = None
                except:
                    value = None
                newdict = {key: value}
                attrdic = None
                if rootkey is not None:
                    self.keyfindandset(out, rootkey, thenode)
                else:
                    if thenode.attributes is not None:
                        tmpattr = dict()
                        if thenode.attributes.length > 0:
                            for attrkey in list(thenode.attributes.keys()):
                                tmpattr.update(
                                    {attrkey: thenode.attributes.get(attrkey).nodeValue})
                            attrdic = {"attr": tmpattr}
                    if key in out:
                        if out[key] is None:
                            if attrdic is not None:
                                if value is None:
                                    out[key] = attrdic
                                else:
                                    valdic = {"value": value}
                                    valdic.update(attrdic)
                                    out[key] = valdic
                            else:
                                out[key] = value
                        elif type(out[key]) == list:
                            if attrdic is not None:
                                newdict.update(attrdic)
                            out[key].append(newdict)
                        elif type(out[key]) == dict:
                            if attrdic is not None:
                                newdict.update(attrdic)
                            out[key].update(newdict)
                        else:
                            tmp = out[key]
                            out[key] = [tmp, value]
                    else:
                        out[key] = value
                        if attrdic is not None:
                            if value is None:
                                newdict[key] = attrdic
                            else:
                                valdic = {"value": value}
                                valdic.update(attrdic)
                                newdict = valdic
                            out[key] = newdict
                self.parseintodict(thenode, level + 1, out, key)
        return out

    def keyfindandset(self, thedict, thekey, thenode):
        # get the key/value pair from the node.
        newvalkey = thenode.nodeName
        value = None
        try:
            value = thenode.childNodes[0].data
            if value.strip() == '':
                value = None
        except:
            value = None
        newval = {newvalkey: value}
        attrdic = None
        if thenode.attributes is not None:
            tmpattr = dict()
            if thenode.attributes.length > 0:
                for key in list(thenode.attributes.keys()):
                    tmpattr.update(
                        {key: thenode.attributes.get(key).nodeValue})
                attrdic = {"attr": tmpattr}
        if attrdic is not None:
            if value is None:
                newval.update({newvalkey: attrdic})
            else:
                valdic = {"value": value}
                newval.update(valdic)
                newval.update(attrdic)
        for key in list(thedict.keys()):
            if key == thekey:
                if isinstance(thedict[key], dict):
                    if newvalkey in thedict[key]:
                        if newval[newvalkey] is not None:
                            tmpdic = thedict[key][newvalkey]
                            thedict[key][newvalkey] = [tmpdic]
                            thedict[key][newvalkey].append(newval)
                        else:
                            if isinstance(thedict[key][newvalkey], list):
                                thedict[key][newvalkey].append(dict())
                            else:
                                tmpdic = thedict[key][newvalkey]
                                thedict[key][newvalkey] = [tmpdic]
                                thedict[key][newvalkey].append(dict())
                    else:
                        thedict[key].update(newval)
                elif isinstance(thedict[key], list):
                    if newvalkey in thedict[key][-1]:
                        thedict[key].append(newval)
                    else:
                        thedict[key][-1].update(newval)
                else:
                    thedict[key] = newval
            if isinstance(thedict[key], dict):
                self.keyfindandset(thedict[key], thekey, thenode)
