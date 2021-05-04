import unittest

from pygopherd.protocols import gemini, gopherp, http, rfc1436, spartan, wap
from pygopherd.testutil import get_testing_protocol


class ProtocolMultiplexerTestCase(unittest.TestCase):
    def test_gopher(self):
        proto = get_testing_protocol("/gopher0-request.txt\n")
        self.assertIsInstance(proto, rfc1436.GopherProtocol)

    def test_secure_gopher(self):
        proto = get_testing_protocol("/gopher0-request.txt\n", use_tls=True)
        self.assertIsInstance(proto, rfc1436.SecureGopherProtocol)

    def test_gopher_plus(self):
        proto = get_testing_protocol("/gopher+-request.txt\t+\n")
        self.assertIsInstance(proto, gopherp.GopherPlusProtocol)

    def test_secure_gopher_plus(self):
        proto = get_testing_protocol("/gopher+-request.txt\t+\n", use_tls=True)
        self.assertIsInstance(proto, gopherp.SecureGopherPlusProtocol)

    def test_http(self):
        proto = get_testing_protocol("GET /http-request.txt HTTP/1.0\n\n")
        self.assertIsInstance(proto, http.HTTPProtocol)

    def test_https(self):
        proto = get_testing_protocol("GET /http-request.txt HTTP/1.0\n\n", use_tls=True)
        self.assertIsInstance(proto, http.HTTPSProtocol)

    def test_wap(self):
        proto = get_testing_protocol("GET /wap/http-request.txt HTTP/1.0\n\n")
        self.assertIsInstance(proto, wap.WAPProtocol)

    def test_gemini(self):
        proto = get_testing_protocol("gemini://example.com\n", use_tls=True)
        self.assertIsInstance(proto, gemini.GeminiProtocol)

    def test_spartan(self):
        proto = get_testing_protocol("localhost / 0\n")
        self.assertIsInstance(proto, spartan.SpartanProtocol)
