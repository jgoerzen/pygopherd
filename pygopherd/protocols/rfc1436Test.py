import unittest, re
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

    def testhandle_file_zipped(self):
        self.config.set("handlers.ZIP.ZIPHandler", "enabled", 'true')
        from pygopherd.handlers import HandlerMultiplexer
        HandlerMultiplexer.handlers = None
        handlerlist = self.config.get("handlers.HandlerMultiplexer", "handlers")
        handlerlist = handlerlist.strip()
        handlerlist = handlerlist[0] + 'ZIP.ZIPHandler, ' + handlerlist[1:]
        self.config.set("handlers.HandlerMultiplexer", "handlers", handlerlist)
        self.proto = GopherProtocol("/testdata.zip/pygopherd/ziponly\n",
                                    self.server,
                                    self.handler, self.rfile, self.wfile,
                                    self.config)
        self.proto.handle()
        self.assertEquals(self.wfile.getvalue(), "ZIPonly\n")

    def testhandle_dir_abstracts(self):
        proto = GopherProtocol("", self.server, self.handler, self.rfile,
                               self.wfile, self.config)
        proto.handle()
        self.assertEquals(proto.selector, '/')
        self.assertEquals(self.logfile.getvalue(),
                          "10.77.77.77 [GopherProtocol/UMNDirHandler]: /\n")
        # Try to make this easy on us to fix.
        actualarr = self.wfile.getvalue().splitlines()
        expectedarr = [
'iThis is the abstract for the testdata directory.\tfake\t(NULL)\t0',
'0README\t/README\tHOSTNAME\t64777\t+',
'1pygopherd\t/pygopherd\tHOSTNAME\t64777\t+',
'9testarchive\t/testarchive.tar\tHOSTNAME\t64777\t+',
'9testarchive.tar.gz\t/testarchive.tar.gz\tHOSTNAME\t64777\t+',
'9testarchive.tgz\t/testarchive.tgz\tHOSTNAME\t64777\t+',
'9testdata\t/testdata.zip\tHOSTNAME\t64777\t+',
'9testdata2\t/testdata2.zip\tHOSTNAME\t64777\t+',
'0testfile\t/testfile.txt\tHOSTNAME\t64777\t+',
'9testfile.txt.gz\t/testfile.txt.gz\tHOSTNAME\t64777\t+',
'iThis is the abstract\tfake\t(NULL)\t0',
'ifor testfile.txt.gz\tfake\t(NULL)\t0']
        expectedarr = [re.sub('HOSTNAME', self.server.server_name, x) for \
                      x in expectedarr]
        self.assertEquals(len(actualarr), len(expectedarr), str(actualarr))
        for i in range(len(actualarr)):
            self.assertEquals(actualarr[i], expectedarr[i])
        # Make sure proper line endings are present.
        self.assertEquals("\r\n".join(actualarr) + "\r\n", self.wfile.getvalue())

    def testhandle_dir_noabstract(self):
        self.config.set("pygopherd", "abstract_headers", "off")
        self.config.set("pygopherd", "abstract_entries", "off")
        proto = GopherProtocol("", self.server, self.handler, self.rfile,
                               self.wfile, self.config)
        proto.handle()
        actualarr = self.wfile.getvalue().splitlines()
        expectedarr = \
             ['0README\t/README\tHOSTNAME\t64777\t+',
              '1pygopherd\t/pygopherd\tHOSTNAME\t64777\t+',
              '9testarchive\t/testarchive.tar\tHOSTNAME\t64777\t+',
              '9testarchive.tar.gz\t/testarchive.tar.gz\tHOSTNAME\t64777\t+',
              '9testarchive.tgz\t/testarchive.tgz\tHOSTNAME\t64777\t+',
              '9testdata\t/testdata.zip\tHOSTNAME\t64777\t+',
              '9testdata2\t/testdata2.zip\tHOSTNAME\t64777\t+',
              '0testfile\t/testfile.txt\tHOSTNAME\t64777\t+',
              '9testfile.txt.gz\t/testfile.txt.gz\tHOSTNAME\t64777\t+']
        expectedarr = [re.sub('HOSTNAME', self.server.server_name, x) for \
                       x in expectedarr]
        self.assertEquals(len(actualarr), len(expectedarr))
        for i in range(len(actualarr)):
            self.assertEquals(actualarr[i], expectedarr[i])

