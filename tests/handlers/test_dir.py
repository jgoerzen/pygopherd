import os
import unittest

from pygopherd import testutil
from pygopherd.handlers.base import VFS_Real
from pygopherd.handlers.dir import DirHandler


class TestDirHandler(unittest.TestCase):
    def setUp(self):
        self.config = testutil.getconfig()
        self.vfs = VFS_Real(self.config)
        self.selector = "/"
        self.protocol = testutil.gettestingprotocol(self.selector, config=self.config)
        self.stat_result = self.vfs.stat(self.selector)

        # Make sure there's no directory cache file from a previous test run
        cachefile = self.config.get("handlers.dir.DirHandler", "cachefile")
        try:
            os.remove(self.vfs.getfspath(self.selector) + "/" + cachefile)
        except OSError:
            pass

    def test_dir_handler(self):
        handler = DirHandler(
            self.selector, "", self.protocol, self.config, self.stat_result, self.vfs
        )

        self.assertTrue(handler.canhandlerequest())
        self.assertTrue(handler.isdir())

        handler.prepare()
        self.assertFalse(handler.fromcache)

        entry = handler.getentry()
        self.assertEqual(entry.mimetype, "application/gopher-menu")
        self.assertEqual(entry.type, "1")

        entries = handler.getdirlist()
        self.assertTrue(entries)

        # Create a second handler to test that it will load from the cached
        # file that the first handler should have created
        handler = DirHandler(
            self.selector, "", self.protocol, self.config, self.stat_result, self.vfs
        )

        handler.prepare()
        self.assertTrue(handler.fromcache)

        cached_entries = handler.getdirlist()
        for a, b in zip(entries, cached_entries):
            self.assertEqual(a.selector, b.selector)
