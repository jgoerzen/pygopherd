import io
import unittest

from pygopherd import testutil
from pygopherd.initialization import init_mimetypes
from pygopherd.protocols.spartan import SpartanProtocol


class TestSpartanProtocol(unittest.TestCase):
    def setUp(self):
        self.config = testutil.get_config()
        self.logfile = testutil.get_string_logger()
        self.rfile = io.BytesIO()
        self.wfile = io.BytesIO()
        self.handler = testutil.get_testing_handler(self.rfile, self.wfile, self.config)

    def get_protocol(self, request):
        return SpartanProtocol(
            request,
            self.handler.server,
            self.handler,
            self.rfile,
            self.wfile,
            self.config,
        )

    def test_spartan_handler(self):
        protocol = self.get_protocol("localhost / 0")
        self.assertTrue(protocol.canhandlerequest())

        protocol.handle()

        response = self.wfile.getvalue().decode(errors="surrogateescape")
        self.assertTrue(response.startswith("2 text/gemini\r\n"))

    @unittest.skipUnless(
        testutil.supports_non_utf8_filenames(),
        reason="Filesystem does not support non-utf8 filenames.",
    )
    def test_non_utf8(self):
        protocol = self.get_protocol("localhost / 0")
        protocol.handle()

        response = self.wfile.getvalue().decode(errors="surrogateescape")
        # The URL should be percent-sign encoded, the description should be
        # backslash replaced.
        self.assertIn("=> /%AE.txt \\xae\n", response)

    def test_not_found(self):
        protocol = self.get_protocol("localhost /dnsajd 0")
        protocol.handle()

        response = self.wfile.getvalue().decode()
        self.assertEqual("4 '/dnsajd' does not exist (no handler found)\r\n", response)

    def test_generate_query_link(self):
        protocol = self.get_protocol("localhost / 0")
        protocol.handle()

        response = self.wfile.getvalue().decode(errors="surrogateescape")
        self.assertIn("=: / Enter a query", response)

    def test_search_request(self):
        self.rfile = io.BytesIO(b"\xae")
        protocol = self.get_protocol("localhost / 2")
        protocol.handle()

        self.assertEqual(protocol.searchrequest, "\udcae")

    def test_detect_mime_type(self):
        init_mimetypes(self.config)

        protocol = self.get_protocol("localhost /testfile.gmi 0")
        protocol.handle()

        response = self.wfile.getvalue().decode(errors="surrogateescape")
        self.assertTrue(response.startswith("2 text/gemini\r\n"))
