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
                         "unknown-address [None/None] IOError: foo\n")

    def testlog_proto_ip(self):
        rfile = StringIO("/NONEXISTANT\n")
        wfile = StringIO()
        handler = testutil.gettestinghandler(rfile, wfile, self.config)
        # handler.handle()
        self.assertEquals(self.stringfile.getvalue(),
             "10.77.77.77 [GopherProtocol/None] FileNotFound: '/NONEXISTANT' does not exist (no handler found)\n")

    def testFileNotFound(self):
        try:
            raise FileNotFound, "TEST STRING"
        except FileNotFound, e:
            self.assertEquals(str(e),
                              "'TEST STRING' does not exist")

        try:
            handler = testutil.gettestinghandler(StringIO("../\n"),
                                                 StringIO(),
                                                 self.config)
            self.fail("Exception was not raised")
        except FileNotFound, e:
            self.assertEquals(str(e),
                              "'../' does not exist (Request may not contain ./, ../, or //)")

