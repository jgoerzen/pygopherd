#!/usr/bin/python

# Python-based gopher server
# Module: test of Gopher Exceptions
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
from io import BytesIO

from pygopherd import GopherExceptions, testutil
from pygopherd.GopherExceptions import FileNotFound


class GopherExceptionsTestCase(unittest.TestCase):
    def setUp(self):
        self.config = testutil.getconfig()
        self.stringfile = testutil.getstringlogger()
        GopherExceptions.tracebacks = 0

    def testlog_basic(self):
        try:
            raise IOError("foo")
        except IOError as e:
            GopherExceptions.log(e)
        self.assertEqual(
            self.stringfile.getvalue(),
            "unknown-address [None/None] EXCEPTION OSError: foo\n",
        )

    def testlog_proto_ip(self):
        rfile = BytesIO(b"/NONEXISTANT\n")
        wfile = BytesIO()
        handler = testutil.gettestinghandler(rfile, wfile, self.config)
        handler.handle()
        self.assertEqual(
            self.stringfile.getvalue(),
            "10.77.77.77 [GopherProtocol/None] EXCEPTION FileNotFound: '/NONEXISTANT' does not exist (no handler found)\n",
        )

    def testFileNotFound(self):
        try:
            raise FileNotFound("TEST STRING")
        except FileNotFound as e:
            self.assertEqual(str(e), "'TEST STRING' does not exist")
