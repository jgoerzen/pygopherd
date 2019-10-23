#!/usr/bin/python

# Python-based gopher server
# Module: test of fileext
# COPYRIGHT #
# Copyright (C) 2002 John Goerzen
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; version 2 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
# END OF COPYRIGHT #

import unittest
from pygopherd import fileext, testutil, initialization

class FileExtTestCase(unittest.TestCase):
    def setUp(self):
        config = testutil.getconfig()
        initialization.initmimetypes(config)
        
    def testinit(self):
        # Was already inited in the initmimetypes, so just do a sanity
        # check.
        self.assertTrue('.txt' in fileext.typemap['text/plain'])
        self.assertTrue('.txt.gz' in fileext.typemap['text/plain'])
        self.assertTrue(not ('.html' in fileext.typemap['text/plain']))
        
