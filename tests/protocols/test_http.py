import io
import unittest

from pygopherd import testutil
from pygopherd.protocols.http import HTTPProtocol


class TestHTTPProtocol(unittest.TestCase):
    def setUp(self):
        self.config = testutil.getconfig()
        self.logfile = testutil.getstringlogger()
        self.rfile = io.BytesIO(b"Accept:text/plain\nHost:localhost.com\n\n")
        self.wfile = io.BytesIO()
        self.handler = testutil.gettestinghandler(self.rfile, self.wfile, self.config)

    def test_http_handler(self):
        request = "GET / HTTP/1.1"
        protocol = HTTPProtocol(
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
        self.assertIn("Content-Type: text/html", response)
        self.assertIn('SRC="/PYGOPHERD-HTTPPROTO-ICONS/text.gif"', response)

    @unittest.skipUnless(
        testutil.supports_non_utf8_filenames(),
        reason="Filesystem does not support non-utf8 filenames.",
    )
    def test_http_hander_non_utf8(self):
        request = "GET / HTTP/1.1"
        protocol = HTTPProtocol(
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
        # Non-UTF8 files should show up in the listing. I don't know how
        # browsers are supposed to render these, but chrome seems to figure
        # it out as a ® symbol.
        self.assertIn('<TD>&nbsp;<A HREF="/%AE.txt"><TT>\udcae.txt', response)

    def test_http_handler_icon(self):
        request = "GET /PYGOPHERD-HTTPPROTO-ICONS/text.gif HTTP/1.1"
        protocol = HTTPProtocol(
            request,
            self.handler.server,
            self.handler,
            self.rfile,
            self.wfile,
            self.config,
        )

        self.assertTrue(protocol.canhandlerequest())

        protocol.handle()
        response = self.wfile.getvalue()
        self.assertIn(b"HTTP/1.0 200 OK", response)
        self.assertIn(b"Content-Type: image/gif", response)
        self.assertIn(b"This art is in the public domain", response)

    def test_http_handler_not_found(self):
        request = "GET /invalid-filename HTTP/1.1"
        protocol = HTTPProtocol(
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
        self.assertIn("HTTP/1.0 404 Not Found", response)
        self.assertIn("Content-Type: text/html", response)
        self.assertIn(
            "&#x27;/invalid-filename&#x27; does not exist (no handler found)", response
        )

    def test_http_handler_search(self):
        request = "GET /?searchrequest=foo%20bar HTTP/1.1"
        protocol = HTTPProtocol(
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
