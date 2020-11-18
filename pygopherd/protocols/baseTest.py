import unittest
import pygopherd.handlers.file
from pygopherd import testutil
from io import BytesIO
from pygopherd.protocols.base import BaseGopherProtocol


class BaseProtocolTestCase(unittest.TestCase):
    def setUp(self):
        self.config = testutil.getconfig()
        self.rfile = BytesIO(b"/testfile.txt\n")
        self.wfile = BytesIO()
        self.logfile = testutil.getstringlogger()
        self.logstr = "10.77.77.77 [BaseGopherProtocol/FileHandler]: /testfile.txt\n"
        self.handler = testutil.gettestinghandler(self.rfile, self.wfile, self.config)
        self.server = self.handler.server
        self.proto = BaseGopherProtocol(
            "/testfile.txt\n",
            self.server,
            self.handler,
            self.rfile,
            self.wfile,
            self.config,
        )

    def testInitBasic(self):
        proto = BaseGopherProtocol(
            "/foo.txt\n", self.server, self.handler, self.rfile, self.wfile, self.config
        )
        assert proto.rfile == self.rfile
        assert proto.wfile == self.wfile
        assert proto.config == self.config
        assert proto.requesthandler == self.handler
        assert proto.requestlist == ["/foo.txt"]
        assert proto.searchrequest == None
        assert proto.handler == None
        assert proto.selector == "/foo.txt"

    def testInitEmpty(self):
        proto = BaseGopherProtocol(
            "\n", self.server, self.handler, self.rfile, self.wfile, self.config
        )
        # It should be rewritten to /
        assert proto.selector == "/"
        assert proto.requestlist == [""]

    def testInitMissingLeadingSlash(self):
        proto = BaseGopherProtocol(
            "foo.txt\n", self.server, self.handler, self.rfile, self.wfile, self.config
        )
        assert proto.selector == "/foo.txt"
        assert proto.requestlist == ["foo.txt"]

    def testInitAddedTrailingSlash(self):
        proto = BaseGopherProtocol(
            "/dir/\n", self.server, self.handler, self.rfile, self.wfile, self.config
        )
        assert proto.selector == "/dir"
        assert proto.requestlist == ["/dir/"]

    def testInitBothSlashProblems(self):
        proto = BaseGopherProtocol(
            "dir/\n", self.server, self.handler, self.rfile, self.wfile, self.config
        )
        assert proto.selector == "/dir"
        assert proto.requestlist == ["dir/"]

    def testInitSplit(self):
        proto = BaseGopherProtocol(
            "foo.txt\t+\n",
            self.server,
            self.handler,
            self.rfile,
            self.wfile,
            self.config,
        )
        assert proto.selector == "/foo.txt"
        assert proto.requestlist == ["foo.txt", "+"]

    def testcanhandlerequest(self):
        assert not self.proto.canhandlerequest()

    def testlog(self):
        # This is a file handler, not a request handler!
        handler = self.proto.gethandler()
        self.proto.log(handler)
        self.assertEqual(self.logfile.getvalue(), self.logstr)

    def testhandle_file(self):
        self.proto.handle()
        self.assertEqual(self.logfile.getvalue(), self.logstr)
        self.assertEqual(self.wfile.getvalue(), b"Test\n")

    def testhandle_notfound(self):
        proto = BaseGopherProtocol(
            "/NONEXISTANT.txt\n",
            self.server,
            self.handler,
            self.rfile,
            self.wfile,
            self.config,
        )
        proto.handle()
        self.assertEqual(
            self.logfile.getvalue(),
            "10.77.77.77 [BaseGopherProtocol/None] EXCEPTION FileNotFound: '/NONEXISTANT.txt' does not exist (no handler found)\n",
        )
        self.assertEqual(
            self.wfile.getvalue(),
            b"3'/NONEXISTANT.txt' does not exist (no handler found)\t\terror.host\t1\r\n",
        )

    # We cannot test handle_dir here because we don't have enough info.

    def testfilenotfound(self):
        self.proto.filenotfound(b"FOO")
        self.assertEqual(self.wfile.getvalue(), b"3FOO\t\terror.host\t1\r\n")

    def testgethandler(self):
        handler = self.proto.gethandler()
        assert isinstance(handler, pygopherd.handlers.file.FileHandler)
        # Make sure caching works.
        assert handler == self.proto.gethandler()

    ## CANNOT TEST: writedir, renderabstract

    def testrenderdirstart(self):
        assert self.proto.renderdirstart("foo") == None

    def testrenderdirend(self):
        assert self.proto.renderdirend("foo") == None

    def testrenderobjinfo(self):
        assert self.proto.renderobjinfo("foo") == None

    def testgroksabstract(self):
        assert not self.proto.groksabstract()
