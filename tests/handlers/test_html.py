import unittest

from pygopherd import testutil
from pygopherd.handlers.base import VFS_Real
from pygopherd.handlers.html import HTMLFileTitleHandler


class TestHTMLHandler(unittest.TestCase):
    def setUp(self):
        self.config = testutil.get_config()
        self.vfs = VFS_Real(self.config)
        self.selector = "/testfile.html"
        self.protocol = testutil.get_testing_protocol(self.selector, config=self.config)
        self.stat_result = self.vfs.stat(self.selector)

    def test_html_handler(self):
        handler = HTMLFileTitleHandler(
            "/testfile.html", "", self.protocol, self.config, self.stat_result, self.vfs
        )

        self.assertTrue(handler.canhandlerequest())

        entry = handler.getentry()
        self.assertEqual(entry.name, "<Gopher Rocks>")
