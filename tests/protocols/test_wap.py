import io
import unittest

from pygopherd import testutil
from pygopherd.protocols.wap import WAPProtocol


class TestWAPProtocol(unittest.TestCase):
    def setUp(self):
        self.config = testutil.getconfig()
        self.logfile = testutil.getstringlogger()
        self.rfile = io.BytesIO(b"Accept:text/plain\nHost:localhost.com\n\n")
        self.wfile = io.BytesIO()
        self.handler = testutil.gettestinghandler(self.rfile, self.wfile, self.config)

    def test_wap_handler(self):
        request = "GET /wap HTTP/1.1"
        protocol = WAPProtocol(
            request,
            self.handler.server,
            self.handler,
            self.rfile,
            self.wfile,
            self.config,
        )

        self.assertTrue(protocol.canhandlerequest())

        protocol.handle()
        self.assertEqual(protocol.httpheaders["host"], "localhost.com")

        response = self.wfile.getvalue().decode(errors="surrogateescape")
        self.assertIn("HTTP/1.0 200 OK", response)
        self.assertIn("Content-Type: text/vnd.wap.wml", response)
        self.assertIn('href="/wap/README">README</a>', response)

    def test_wap_handler_not_found(self):
        request = "GET /wap/invalid-filename HTTP/1.1"
        protocol = WAPProtocol(
            request,
            self.handler.server,
            self.handler,
            self.rfile,
            self.wfile,
            self.config,
        )

        self.assertTrue(protocol.canhandlerequest())

        protocol.handle()
        response = self.wfile.getvalue().decode()
        self.assertIn("HTTP/1.0 200 Not Found", response)
        self.assertIn("Content-Type: text/vnd.wap.wml", response)
        self.assertIn('<card id="index" title="404 Error" newcontext="true">', response)

    def test_wap_handler_search(self):
        request = "GET /wap/?searchrequest=foo%20bar HTTP/1.1"
        protocol = WAPProtocol(
            request,
            self.handler.server,
            self.handler,
            self.rfile,
            self.wfile,
            self.config,
        )

        self.assertTrue(protocol.canhandlerequest())

        protocol.handle()
        self.assertEqual(protocol.searchrequest, "foo bar")
