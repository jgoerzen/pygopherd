import unittest
from pygopherd import testutil
from StringIO import StringIO
from pygopherd.protocols.base import BaseGopherProtocol

class BaseProtocolTestCase(unittest.TestCase):
    def setUp(self):
        self.config = testutil.getconfig()
        self.rfile = StringIO()
        self.wfile = StringIO()
        self.handler = testutil.gettestinghandler(self.rfile, self.wfile,
                                                  self.config)
        self.server = self.handler.server

    def testInit(self):
        proto = BaseGopherProtocol('/foo.txt', self.server, self.handler,
                                   self.rfile, self.wfile, self.config)
        assert proto.rfile == self.rfile
        assert proto.wfile == self.wfile
        assert proto.config == self.config
        assert proto.requesthandler == self.handler
        assert proto.requestlist == ['/foo.txt']
        assert proto.searchrequest == None
        assert proto.handler == None
        assert proto.selector == '/foo.txt'
        
