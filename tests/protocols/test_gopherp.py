import io
import unittest

from pygopherd import testutil
from pygopherd.protocols.gopherp import GopherPlusProtocol


class TestGopherPlusProtocol(unittest.TestCase):
    def setUp(self):
        self.config = testutil.get_config()
        self.logfile = testutil.get_string_logger()
        self.rfile = io.BytesIO()
        self.wfile = io.BytesIO()
        self.handler = testutil.get_testing_handler(self.rfile, self.wfile, self.config)

    def test_get_file(self):
        request = "/README\t+"
        protocol = GopherPlusProtocol(
            request,
            self.handler.server,
            self.handler,
            self.rfile,
            self.wfile,
            self.config,
        )

        self.assertTrue(protocol.canhandlerequest())

        protocol.handle()
        self.assertEqual(protocol.gopherpstring, "+")
        self.assertEqual(protocol.handlemethod, "documentonly")

        response = self.wfile.getvalue().decode()

        expected = [
            "+142",
            "This directory contains data for the unit tests.",
            "",
            "Some tests are dependant upon the precise length of files; those files are",
            "added with -kb.",
            "",
        ]
        self.assertListEqual(response.splitlines(keepends=False), expected)

        # 142 byte filesize + 6 bytes for the "+142\r\n"
        self.assertTrue(len(response.encode()), 148)

    def test_file_not_found(self):
        protocol = GopherPlusProtocol(
            "/invalid-selector\t+",
            self.handler.server,
            self.handler,
            self.rfile,
            self.wfile,
            self.config,
        )

        self.assertTrue(protocol.canhandlerequest())

        protocol.handle()
        self.assertEqual(protocol.gopherpstring, "+")
        self.assertEqual(protocol.handlemethod, "documentonly")

        response = self.wfile.getvalue().decode()

        expected = [
            "--2",
            "1 Unconfigured Pygopherd Admin <pygopherd@nowhere.nowhere>",
            "'/invalid-selector' does not exist (no handler found)",
        ]

        self.assertListEqual(response.splitlines(keepends=False), expected)

    def test_get_directory(self):
        protocol = GopherPlusProtocol(
            "/gopherplus\t+",
            self.handler.server,
            self.handler,
            self.rfile,
            self.wfile,
            self.config,
        )

        self.assertTrue(protocol.canhandlerequest())

        protocol.handle()
        response = self.wfile.getvalue().decode()

        lines = response.splitlines(keepends=False)

        self.assertEqual(lines[0], "+-2")
        self.assertEqual(lines[1][-2:], "\t+")
        self.assertEqual(lines[2][-2:], "\t+")

    def test_get_file_info(self):
        protocol = GopherPlusProtocol(
            "/gopherplus/README\t!",
            self.handler.server,
            self.handler,
            self.rfile,
            self.wfile,
            self.config,
        )

        self.assertTrue(protocol.canhandlerequest())

        protocol.handle()
        response = self.wfile.getvalue().decode()

        self.assertIn("+VIEWS:\r\n text/plain: <0k>", response)
        self.assertIn("+INFO: 0README\t", response)
        self.assertIn("+ADMIN:", response)
        self.assertIn("+3D:\r\n this is a gopher+ info attribute", response)

    def test_get_directory_info(self):
        protocol = GopherPlusProtocol(
            "/gopherplus\t$",
            self.handler.server,
            self.handler,
            self.rfile,
            self.wfile,
            self.config,
        )

        self.assertTrue(protocol.canhandlerequest())

        protocol.handle()
        response = self.wfile.getvalue().decode()

        self.assertIn("+INFO: 0README\t", response)
        self.assertIn("+INFO: 0testfile\t", response)

    def test_ask_query(self):
        """
        Not supported by pygopherd :(
        """
