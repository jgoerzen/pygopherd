import unittest
from StringIO import StringIO
from pygopherd.protocols import ProtocolMultiplexer
from pygopherd import testutil
import pygopherd.protocols

class ProtocolMultiplexerTestCase(unittest.TestCase):
    def setUp(self):
        self.config = testutil.getconfig()

    # Just a bunch of test cases for each different protocol -- make
    # sure we find the right one.

    def getproto(self, request):
        handler = testutil.gettestinghandler(StringIO(request), StringIO(),
                                             self.config)
        return ProtocolMultiplexer.getProtocol(request,
                                               handler.server,
                                               handler,
                                               handler.rfile,
                                               handler.wfile,
                                               self.config)

    def testGoToGopher(self):
        assert isinstance(self.getproto("/gopher0-request.txt\n"), pygopherd.protocols.rfc1436.GopherProtocol)
        
