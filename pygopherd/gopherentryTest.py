#!/usr/bin/python2.2

# Python-based gopher server
# Module: test of gopherentry
# COPYRIGHT #
# Copyright (C) 2002 John Goerzen
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
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

import unittest, os, stat
from pygopherd import testutil
from pygopherd.gopherentry import GopherEntry

class GopherEntryTestCase(unittest.TestCase):
    def setUp(self):
        self.config = testutil.getconfig()

    def assertEntryMatches(self, conditions, entry, testname):
        for field, value in conditions.items():
            self.assertEquals(value, getattr(entry, field),
                              "%s: Field %s expected %s but was %s" % \
                              (testname, field, value, getattr(entry, field)))

    def testinit(self):
        entry = GopherEntry('/NONEXISTANT', self.config)
        conditions = {'selector' : '/NONEXISTANT',
                      'config' : self.config,
                      'populated' : 0,
                      'gopherpsupport' : 0
                      }
        for x in ['fspath', 'type', 'name', 'host', 'port', 'mimetype',
                  'encodedmimetype', 'size', 'encoding', 'language', 'ctime',
                  'mtime']:
            conditions[x] = None
        self.assertEntryMatches(conditions, entry, 'testinit')

    def testpopulate_basic(self):
        fspath = self.config.get("pygopherd", "root") + '/testfile.txt'
        statval = os.stat(fspath)
        conditions = {'selector' : '/testfile.txt',
                      'config' : self.config,
                      'fspath' : fspath,
                      'type' : '0',
                      'name' : 'testfile.txt',
                      'host' : None,
                      'port' : None,
                      'mimetype' : 'text/plain',
                      'encodedmimetype' : None,
                      'encoding' : None,
                      'populated' : 1,
                      'language' : None,
                      'gopherpsupport' : 1,
                      'ctime' : statval[9],
                      'mtime' : statval[8],
                      'size' : 5,
                      'num' : 0}
                      
        entry = GopherEntry('/testfile.txt', self.config)
        entry.populatefromfs(fspath)
        self.assertEntryMatches(conditions, entry, 'testpopulate_basic')

        # Also try it with passed statval.

        entry = GopherEntry('/testfile.txt', self.config)
        entry.populatefromfs(fspath, statval)
        self.assertEntryMatches(conditions, entry,
                                'testpopulate_basic with cached stat')
    
        
