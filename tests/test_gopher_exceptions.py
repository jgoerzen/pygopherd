#!/usr/bin/python

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
