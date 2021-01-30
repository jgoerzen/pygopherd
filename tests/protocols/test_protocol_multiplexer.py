import unittest

import pygopherd.protocols
from pygopherd import testutil


class ProtocolMultiplexerTestCase(unittest.TestCase):
    def setUp(self):
        self.config = testutil.get_config()

    # Just a bunch of test cases for each different protocol -- make
    # sure we find the right one.

    def testGoToGopher(self):
        assert isinstance(
            testutil.get_testing_protocol("/gopher0-request.txt\n"),
            pygopherd.protocols.rfc1436.GopherProtocol,
        )

    def testGoToHTTP(self):
        assert isinstance(
            testutil.get_testing_protocol("GET /http-request.txt HTTP/1.0\n\n"),
            pygopherd.protocols.http.HTTPProtocol,
        )

    def testGoToGopherPlus(self):
        assert isinstance(
            testutil.get_testing_protocol("/gopher+-request.txt\t+\n"),
            pygopherd.protocols.gopherp.GopherPlusProtocol,
        )
