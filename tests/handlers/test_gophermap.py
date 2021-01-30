import unittest

from pygopherd import testutil
from pygopherd.handlers.base import VFS_Real
from pygopherd.handlers.gophermap import BuckGophermapHandler


class TestBuckGophermapHandler(unittest.TestCase):
    def setUp(self):
        self.config = testutil.get_config()
        self.vfs = VFS_Real(self.config)
        self.selector = "/bucktooth"
        self.protocol = testutil.get_testing_protocol(self.selector, config=self.config)
        self.stat_result = self.vfs.stat(self.selector)

    def test_buck_gophermap_handler(self):
        handler = BuckGophermapHandler(
            self.selector, "", self.protocol, self.config, self.stat_result, self.vfs
        )

        self.assertTrue(handler.canhandlerequest())
        self.assertTrue(handler.isdir())

        handler.prepare()
        entry = handler.getentry()
        self.assertEqual(entry.mimetype, "application/gopher-menu")
        self.assertEqual(entry.type, "1")

        entries = handler.getdirlist()
        self.assertTrue(entries)

        expected = [
            ("i", "hello world", "fake", "(NULL)", 0),
            ("1", "filename", "/bucktooth/filename", None, None),
            ("1", "filename", "/bucktooth/README", None, None),
            ("1", "filename", "/bucktooth/selector", "hostname", None),
            ("1", "filename", "/bucktooth/selector", "hostname", 69),
        ]
        for i, entry in enumerate(entries):
            self.assertEqual(entry.type, expected[i][0])
            self.assertEqual(entry.name, expected[i][1])
            self.assertEqual(entry.selector, expected[i][2])
            self.assertEqual(entry.host, expected[i][3])
            self.assertEqual(entry.port, expected[i][4])
