#!/usr/bin/python2.2

# Python-based gopher server
# Module: test of Gopher Exceptions
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

import unittest
from StringIO import StringIO
from pygopherd import logger, initialization, GopherExceptions, testutil
from pygopherd.GopherExceptions import FileNotFound
from pygopherd.protocols import rfc1436

class GopherExceptionsTestCase(unittest.TestCase):
    def setUp(self):
        self.stringfile = StringIO()
        self.config = testutil.getconfig()
        self.stringfile = testutil.getstringlogger()
        GopherExceptions.tracebacks = 0

    def testlog_basic(self):
        try:
            raise IOError, "foo"
        except IOError, e:
            GopherExceptions.log(e)
        self.assertEqual(self.stringfile.getvalue(),
                         "unknown-address [None/None] EXCEPTION IOError: foo\n")

    def testlog_proto_ip(self):
        rfile = StringIO("/NONEXISTANT\n")
        wfile = StringIO()
        handler = testutil.gettestinghandler(rfile, wfile, self.config)
        handler.handle()
        # handler.handle()
        self.assertEquals(self.stringfile.getvalue(),
             "10.77.77.77 [GopherProtocol/None] EXCEPTION FileNotFound: '/NONEXISTANT' does not exist (no handler found)\n")

    def testFileNotFound(self):
        try:
            raise FileNotFound, "TEST STRING"
        except FileNotFound, e:
            self.assertEquals(str(e),
                              "'TEST STRING' does not exist")

