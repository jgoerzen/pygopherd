import unittest
from pygopherd.protocols.rfc1436 import GopherProtocol
from pygopherd import testutil
from StringIO import StringIO

class RFC1436TestCase(unittest.TestCase):
    def setUp(self):
        self.config = testutil.getconfig()
        self.rfile = StringIO("/testfile.txt\n")
        self.wfile = StringIO()
        self.logfile = testutil.getstringlogger()
        self.handler = testutil.gettestinghandler(self.rfile, self.wfile,
                                                  self.config)
        self.server = self.handler.server
        self.proto = GopherProtocol("/testfile.txt\n", self.server,
                                    self.handler, self.rfile, self.wfile,
                                    self.config)

    def testcanhandlerequest(self):
        assert self.proto.canhandlerequest()
        proto = GopherProtocol("/testfile.txt\tsearch\n",
                               self.server, self.handler, self.rfile,
                               self.wfile, self.config)
        assert proto.canhandlerequest()
        self.assertEquals(proto.selector, '/testfile.txt')
        self.assertEquals(proto.searchrequest, "search")

    def testrenderobjinfo(self):
        expected = "0testfile.txt\t/testfile.txt\t%s\t%d\t+\r\n" % \
                   (self.server.server_name, self.server.server_port)
        self.assertEquals(self.proto.renderobjinfo(self.proto.gethandler().getentry()),
                          expected)

    def testhandle_file(self):
        self.proto.handle()
        self.assertEquals(self.logfile.getvalue(),
                          "10.77.77.77 [GopherProtocol/FileHandler]: /testfile.txt\n")
        self.assertEquals(self.wfile.getvalue(), "Test\n")

    def testhandle_dir(self):
        proto = GopherProtocol("", self.server, self.handler, self.rfile,
                               self.wfile, self.config)
        proto.handle()
        self.assertEquals(proto.selector, '/')
        self.assertEquals(self.logfile.getvalue(),
                          "10.77.77.77 [GopherProtocol/UMNDirHandler]: /\n")
        self.assertEquals(self.wfile.getvalue(),
                          'iThis is the abstract for the testdata directory.\tfake\t(NULL)\t0\r\n1CVS\t/CVS\terwin.complete.org\t64777\t+\r\n0README\t/README\terwin.complete.org\t64777\t+\r\n1pygopherd\t/pygopherd\terwin.complete.org\t64777\t+\r\n9testarchive.tar\t/testarchive.tar\terwin.complete.org\t64777\t+\r\n9testarchive.tar.gz\t/testarchive.tar.gz\terwin.complete.org\t64777\t+\r\n9testarchive.tgz\t/testarchive.tgz\terwin.complete.org\t64777\t+\r\n0testfile.txt\t/testfile.txt\terwin.complete.org\t64777\t+\r\n9testfile.txt.gz\t/testfile.txt.gz\terwin.complete.org\t64777\t+\r\niThis is the abstract\tfake\t(NULL)\t0\r\nifor testfile.txt.gz\tfake\t(NULL)\t0\r\n')
        
