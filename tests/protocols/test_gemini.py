import io
import unittest

from pygopherd import testutil
from pygopherd.initialization import init_mimetypes
from pygopherd.protocols.gemini import GeminiProtocol


class TestGeminiProtocol(unittest.TestCase):
    def setUp(self):
        self.config = testutil.get_config()
        self.logfile = testutil.get_string_logger()
        self.rfile = io.BytesIO()
        self.wfile = io.BytesIO()
        self.handler = testutil.get_testing_handler(
            self.rfile, self.wfile, self.config, use_tls=True
        )

    def get_protocol(self, request):
        return GeminiProtocol(
            request,
            self.handler.server,
            self.handler,
            self.rfile,
            self.wfile,
            self.config,
        )

    def test_gemini_handler(self):
        protocol = self.get_protocol("gemini://localhost")
        self.assertTrue(protocol.canhandlerequest())

        protocol.handle()

        response = self.wfile.getvalue().decode(errors="surrogateescape")
        self.assertTrue(response.startswith("20 text/gemini\r\n"))

    def test_optional_trailing_slash(self):
        # The page should load with or without the trailing slash
        protocol = self.get_protocol("gemini://localhost/")
        protocol.handle()

        response = self.wfile.getvalue().decode(errors="surrogateescape")
        self.assertTrue(response.startswith("20 text/gemini\r\n"))

    @unittest.skipUnless(
        testutil.supports_non_utf8_filenames(),
        reason="Filesystem does not support non-utf8 filenames.",
    )
    def test_non_utf8(self):
        protocol = self.get_protocol("gemini://localhost/")
        protocol.handle()

        response = self.wfile.getvalue().decode(errors="surrogateescape")
        # The URL should be percent-sign encoded, the description should be
        # backslash replaced.
        self.assertIn("=> /%AE.txt \\xae\n", response)

    def test_not_found(self):
        protocol = self.get_protocol("gemini://localhost/dnsajd")
        protocol.handle()

        response = self.wfile.getvalue().decode()
        self.assertEqual("51 '/dnsajd' does not exist (no handler found)\r\n", response)

    def test_generate_query_link(self):
        protocol = self.get_protocol("gemini://localhost")
        protocol.handle()

        response = self.wfile.getvalue().decode(errors="surrogateescape")
        self.assertIn("=> /GEMINI-QUERY/ Enter a query", response)

    def test_prompt_query(self):
        protocol = self.get_protocol("gemini://localhost/GEMINI-QUERY/some/path")
        protocol.handle()

        response = self.wfile.getvalue().decode(errors="surrogateescape")
        self.assertEqual("10 Enter input\r\n", response)

    def test_submit_query(self):
        protocol = self.get_protocol("gemini://localhost/GEMINI-QUERY/some/path?%AE")
        protocol.handle()

        response = self.wfile.getvalue().decode(errors="surrogateescape")
        self.assertEqual("30 /some/path?%AE\r\n", response)

    def test_search_request(self):
        protocol = self.get_protocol("gemini://localhost?%AE")
        protocol.handle()

        self.assertEqual(protocol.searchrequest, "\udcae")

    def test_detect_mime_type(self):
        init_mimetypes(self.config)

        protocol = self.get_protocol("gemini://localhost/testfile.gmi")
        protocol.handle()

        response = self.wfile.getvalue().decode(errors="surrogateescape")
        self.assertTrue(response.startswith("20 text/gemini\r\n"))
